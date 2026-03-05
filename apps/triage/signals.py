"""



apps/triage/signals.py







Pre-save signal for TriageSession: automatically enriches village/district



coordinates via OpenStreetMap Nominatim before the record hits the database.







HOW IT WORKS



────────────



1. Any time a TriageSession is about to be saved (create OR update), this



   signal fires.



2. If village + district are present AND no GPS coordinates exist yet, it:



      a. Checks VillageCoordinates cache (no external call needed)



      b. Falls back to Nominatim if not cached, then writes to cache



3. The fetched lat/lng are written directly onto the instance so the caller



   doesn't need to do anything special — `session.save()` is enough.







REGISTRATION



────────────



Add to apps/triage/apps.py:







    class TriageConfig(AppConfig):



        name = "apps.triage"







        def ready(self):



            import apps.triage.signals  # noqa: F401







RATE LIMITING



─────────────



Nominatim requires ≤ 1 request/second. The shared module-level timestamp in



intake_validation.fetch_coordinates_from_nominatim handles this automatically.



To avoid hammering Nominatim on bulk imports, only missing coordinates trigger



an API call; cached hits are instant.



"""







import logging







from django.db import models



from django.db.models.signals import pre_save, post_save



from django.dispatch import receiver







from apps.triage.models import TriageSession, VillageCoordinates



from apps.triage.tools.intake_validation import fetch_coordinates_from_nominatim



from apps.facilities.tools.facility_matching import FacilityMatchingTool



from apps.facilities.models import FacilityRouting







logger = logging.getLogger(__name__)











# ─────────────────────────────────────────────────────────────────────────────



# Helper



# ─────────────────────────────────────────────────────────────────────────────







def _coordinates_already_present(instance: TriageSession) -> bool:



    """Return True if GPS coordinates are already set on the instance."""



    return (



        instance.device_location_lat is not None



        and instance.device_location_lng is not None



    )











def _location_fields_present(instance: TriageSession) -> bool:



    """Return True if both village and district are non-empty strings."""



    return bool(



        instance.village and instance.village.strip()



        and instance.district and instance.district.strip()



    )











def _try_cache(village: str, district: str):



    """



    Look up coordinates from the VillageCoordinates cache.



    Bumps lookup_count atomically on a hit.







    Returns (lat, lng) or (None, None).



    """



    try:



        cached = VillageCoordinates.objects.get(



            village__iexact=village.strip(),



            district__iexact=district.strip(),



        )



        # Atomic increment — safe under concurrent requests



        VillageCoordinates.objects.filter(pk=cached.pk).update(



            lookup_count=models.F("lookup_count") + 1



        )



        logger.debug(



            "Coordinate cache hit for %s, %s → (%s, %s)",



            village, district, cached.latitude, cached.longitude,



        )



        return cached.latitude, cached.longitude



    except VillageCoordinates.DoesNotExist:



        return None, None











def _write_cache(village: str, district: str, lat: float, lng: float) -> None:



    """



    Persist a freshly fetched coordinate pair to the cache.



    Uses get_or_create to avoid race-condition duplicates.



    """



    VillageCoordinates.objects.get_or_create(



        village__iexact=village.strip(),



        district__iexact=district.strip(),



        defaults={



            "village": village.strip(),



            "district": district.strip(),



            "latitude": lat,



            "longitude": lng,



        },



    )



    logger.debug(



        "Coordinate cache written for %s, %s → (%s, %s)",



        village, district, lat, lng,



    )











def enrich_triage_session_coordinates(instance: TriageSession) -> None:



    """



    Core enrichment logic — mutates *instance* in place.



    Extracted as a standalone function so it can be called from management



    commands / data migrations without going through the signal path.



    """



    if _coordinates_already_present(instance):



        logger.debug(



            "Skipping geocoding for %s — coordinates already set.",



            instance.patient_token,



        )



        return







    if not _location_fields_present(instance):



        logger.debug(



            "Skipping geocoding for %s — village or district missing.",



            instance.patient_token,



        )



        return







    village  = instance.village.strip()



    district = instance.district.strip()







    # ── 1. Cache lookup (free) ────────────────────────────────────────────



    lat, lng = _try_cache(village, district)







    # ── 2. Nominatim fallback (rate-limited to 1 req/s) ──────────────────



    if lat is None:



        logger.info(



            "Fetching coordinates from Nominatim for %s, %s", village, district



        )



        lat, lng = fetch_coordinates_from_nominatim(village, district)







        if lat is not None:



            _write_cache(village, district, lat, lng)



        else:



            logger.warning(



                "Nominatim returned no results for %s, %s", village, district



            )



            return   # Leave coordinates as NULL — do not assign None explicitly







    # ── 3. Apply to instance ──────────────────────────────────────────────



    instance.device_location_lat = lat



    instance.device_location_lng = lng



    logger.info(



        "Enriched TriageSession %s with coordinates: %.6f, %.6f",



        instance.patient_token, lat, lng,



    )











# ─────────────────────────────────────────────────────────────────────────────



# Signal handler



# ─────────────────────────────────────────────────────────────────────────────







@receiver(pre_save, sender=TriageSession)



def triage_session_pre_save(sender, instance: TriageSession, **kwargs) -> None:



    """



    Fires before every TriageSession INSERT or UPDATE.







    Only triggers coordinate enrichment when:



      • Both village and district are present



      • No coordinates are already set on the instance







    This keeps the signal cheap for updates that don't touch location fields.



    """



    enrich_triage_session_coordinates(instance)











# ─────────────────────────────────────────────────────────────────────────────



# AUTOMATIC FACILITY ROUTING



# ─────────────────────────────────────────────────────────────────────────────







@receiver(post_save, sender=TriageSession)



def triage_session_post_save(sender, instance: TriageSession, created: bool, **kwargs) -> None:



    """



    Automatically route completed triage sessions to appropriate facilities.



    Triggers when session is completed and has location data.



    """



    # Only route completed sessions with district info



    if instance.status != 'completed':



        return



    



    if not instance.district:



        logger.debug(f"Skipping routing for {instance.patient_token} — no district")



        return



    



    # Check if already routed



    if FacilityRouting.objects.filter(patient_token=instance.patient_token).exists():



        logger.debug(f"Already routed: {instance.patient_token}")



        return



    



    try:



        # Create routing record



        routing = FacilityRouting.objects.create(



            patient_token=instance.patient_token,



            triage_session_id=str(instance.id),



            primary_symptom=instance.complaint_group or 'unknown',



            risk_level=instance.risk_level or 'medium',



            patient_village=instance.village,



            patient_district=instance.district,



            routing_status='pending'



        )



        



        # Use matching tool to find best facility



        matcher = FacilityMatchingTool()



        candidates = matcher.find_candidate_facilities(routing)



        



        if candidates:



            # Assign to best matching facility



            best_candidate = candidates[0]



            routing.assigned_facility = best_candidate.facility



            routing.facility_match_score = best_candidate.match_score



            routing.save()



            



            logger.info(



                f"✅ Routed patient {instance.patient_token} to {best_candidate.facility.name} "



                f"(score: {best_candidate.match_score:.2f})"



            )



        else:



            logger.warning(f"No facility match found for {instance.patient_token}")



            



    except Exception as e:



        logger.error(f"Failed to route patient {instance.patient_token}: {e}")