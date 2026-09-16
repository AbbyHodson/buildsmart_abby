from django import forms

class BuildingForm(forms.Form):
    BUILDING_TYPE_CHOICES = [
        ("Aircraft traffic control & operations", "Aircraft traffic control & operations"),
        ("Ammunition & explosives storage magazine", "Ammunition & explosives storage magazine"),
        ("Aircraft maintenance hangar", "Aircraft maintenance hangar"),
        ("Communications", "Communications"),
        ("Family housing", "Family housing"),
        ("Family service center", "Family service center"),
        ("Industrial utilities & fire protection", "Industrial utilities & fire protection"),
        ("Lodging", "Lodging"),
        ("Maintenance shop", "Maintenance shop"),
        ("Office", "Office"),
        ("Laboratories", "Laboratories"),
        ("Recreation & culture", "Recreation & culture"),
        ("Retail & grocery store", "Retail & grocery store"),
        ("Training & academic instruction", "Training & academic instruction"),
        ("Unaccompanied housing (barracks)", "Unaccompanied housing (barracks)"),
        ("Warehouse/storage", "Warehouse/storage"),
        ("Public service", "Public service"),
        ("Ship operational", "Ship operational"),
        ("Security", "Security"),
        ("Medical facilities", "Medical facilities"),
        ("Fire station", "Fire station"),
        ("Dining", "Dining"),
        ("Armory", "Armory")
    ]

    location = forms.CharField(
        label="Location",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "id": "id_location"})
    )

    building_type = forms.ChoiceField(
        label="Building type",
        choices=BUILDING_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    square_footage = forms.IntegerField(
        label="Building size (sq. ft)",
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    construction_year = forms.IntegerField(
        min_value=2025,
        max_value=2050,
        initial=2025,
        widget=forms.NumberInput(attrs={"type": "range", "step": 1}),
    )
    
    reuse_materials = forms.BooleanField(
        label="Reuse materials?",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    old_location = forms.CharField(
        label="Location",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "id": "old_id_location"}),
        required=False
    )

    old_building_type = forms.ChoiceField(
        label="Building type",
        choices=BUILDING_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False
    )

    old_building_square_footage = forms.IntegerField(
        label="Building size (sq. ft)",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False
    )    

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("reuse_materials"):
            for field in ("old_location", "old_building_type", "old_building_square_footage"):
                if not cleaned.get(field):
                    self.add_error(field, "Required when reusing materials.")
        return cleaned