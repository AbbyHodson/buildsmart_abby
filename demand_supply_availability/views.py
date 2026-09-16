from django.shortcuts import render
from .forms import BuildingForm
from .est_base_demand import est_base_demand
import requests
import os
import logging
import requests
import json
from django.conf import settings
from django.core.cache import cache

GOOGLE_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

logger = logging.getLogger(__name__)

def get_state_from_location(location):
    """Return the US state for a user-specified location, or None."""
    key = f"geocode_state:{location.strip().lower()}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": location, "key": settings.GOOGLE_MAPS_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Geocoding request failed for %r: %s", location, exc)
        return None

    data = response.json()
    status = data.get("status")

    if status != "OK":
        logger.warning("Geocoding returned %s for %r: %s",
                       status, location, data.get("error_message", ""))
        return None

    state = None
    for component in data["results"][0]["address_components"]:
        if "administrative_area_level_1" in component["types"]:
            state = component["long_name"]
            break

    if state is None:
        logger.warning("No state component found for %r", location)
        return None

    cache.set(key, state, 60 * 60 * 24 * 30)
    return state

def index(request):
    context = {}

    if request.method == "POST":
        form = BuildingForm(request.POST)
        if form.is_valid():
            location = form.cleaned_data["location"]
            state = get_state_from_location(location)

            if not state:
                form.add_error("location", "Couldn't determine a US state from that location. Try adding a state or ZIP code.")
            else:
                reuse_materials = form.cleaned_data["reuse_materials"]
                results = est_base_demand(
                    new_building_types=[form.cleaned_data["building_type"]],
                    new_building_sizes=[form.cleaned_data["square_footage"]],
                    state=state,
                    reused_materials=reuse_materials,
                    old_building_types=[form.cleaned_data["old_building_type"]] if reuse_materials else None,
                    old_building_sizes=[form.cleaned_data["old_building_square_footage"]] if reuse_materials else None,
                )
                context["chart_data"] = json.dumps(results)

    else:
        form = BuildingForm()
    
    context["form"] = form
    return render(request, "demand_supply_availability/index.html", context)