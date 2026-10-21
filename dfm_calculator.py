# dfm_calculator.py

def calculate_advanced_dfm_analysis(
    material, 
    volume_cm3, 
    weight_kg, 
    raw_weight_kg=None, 
    complexity_level="Medium", 
    machine_type="3-axlig CNC", 
    tolerance_class="Standard (ISO 2768-m)", 
    surface_finish="Standard (Ra 3.2)", 
    batch_size=1
):
    material_prices = {
        "Aluminium (Al6061-T6)": 55.0,
        "Stål (S235JR)": 18.0,
        "Rostfritt Stål (SS2348)": 75.0,
        "Titan (Grade 5)": 420.0,
        "Plast (POM / Delrin)": 90.0
    }
    
    hourly_rates = {
        "3-axlig CNC": 750.0,
        "4-axlig CNC": 950.0,
        "5-axlig CNC": 1250.0
    }
    
    complexity_factors = {
        "Låg (Enkel platta/profil)": 0.7,
        "Medium (Standardfräsning)": 1.0,
        "Hög (Komplicerade 3D-former & djupa fickor)": 1.6
    }
    
    tolerance_multiplier = 1.25 if "Tät" in tolerance_class or "Hög" in tolerance_class else 1.0
    surface_multiplier = 1.15 if "Fin" in surface_finish or "Ra 1.6" in surface_finish else 1.0
    
    price_per_kg = material_prices.get(material, 55.0)
    raw_material_cost = weight_kg * price_per_kg
    
    cnc_hourly_rate = hourly_rates.get(machine_type, 850.0)
    base_factor = complexity_factors.get(complexity_level, 1.0)
    
    machining_time_minutes = (volume_cm3 ** 0.58) * 4.2 * base_factor * tolerance_multiplier * surface_multiplier
    machining_time_hours = machining_time_minutes / 60.0
    machining_cost = machining_time_hours * cnc_hourly_rate
    
    setup_cost = 3000.0 if "5-axlig" in machine_type else 1800.0
    unit_setup_cost = setup_cost / max(batch_size, 1)
    
    total_unit_cost = raw_material_cost + machining_cost + unit_setup_cost
    
    co2_factors = {
        "Aluminium (Al6061-T6)": 8.5,
        "Stål (S235JR)": 2.1,
        "Rostfritt Stål (SS2348)": 4.5,
        "Titan (Grade 5)": 35.0,
        "Plast (POM / Delrin)": 3.2
    }
    factor = co2_factors.get(material, 5.0)
    co2_emissions_kg = weight_kg * factor

    scrap_weight = (raw_weight_kg - weight_kg) if raw_weight_kg and raw_weight_kg > weight_kg else weight_kg * 0.3
    
    return {
        "raw_material_cost": raw_material_cost,
        "machining_time_minutes": machining_time_minutes,
        "machining_cost": machining_cost,
        "setup_cost": setup_cost,
        "total_unit_cost": total_unit_cost,
        "cnc_hourly_rate": cnc_hourly_rate,
        "co2_emissions_kg": co2_emissions_kg,
        "scrap_weight_kg": scrap_weight
    }