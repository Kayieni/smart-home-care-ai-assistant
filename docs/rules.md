Activity	Condition
wake_up	bed empty + bedroom motion
hygiene	water flow + soap vibration
eating	fridge open + kitchen motion
medication	medicine box vibration
cooking	stove ON
leaving_home	door open + hallway motion


1. Hygiene — Wash hands after toilet (A)
Sensors:
Toilet occupancy sensor
Water flow sensor (sink)
Soap vibration sensor
Rule:
IF toilet_used
AND water_flow_detected
AND soap_used
→ hygiene_completed
Risk if NOT satisfied:
hygiene_missing

2. Kitchen Safety — Stove/Oven monitoring (A)
Sensors:
Smart plug (stove/oven)
Temperature sensor
Rule:
IF stove_power == ON
AND no_motion_in_kitchen FOR > X minutes
→ cooking_risk
IF stove_power == ON
AND resident_location != kitchen
→ hazard_stove_left_on

3. Door Exit Monitoring (A)
Sensors:
Door contact sensor
Hallway motion sensor
Rule:
IF door_open
AND time BETWEEN 00:00–05:00
→ night_exit_risk
IF door_open
AND hallway_motion_detected
→ leaving_home

4. Bed Exit / Wake-up (A)
Sensors:
Bed pressure sensor
Bedroom PIR motion
Rule:
IF bed_pressure == empty
AND bedroom_motion == true
→ wake_up

5. Medication intake (A)
Sensors:
Medicine box vibration sensor
Rule:
IF medicine_box_vibration_detected
→ medication_taken
Risk:
IF time > scheduled_medication_time
AND no_vibration_detected
→ medication_missed

6. Water heater left ON (B)
Sensors:
Smart plug (heater)
Rule:
IF water_heater_power == ON
AND duration > threshold (e.g. 30 min)
→ heater_risk

7. Fridge usage monitoring (B)
Sensors:
Fridge contact sensor
Kitchen motion sensor
Rule:
IF fridge_open
AND kitchen_motion_detected
→ eating_activity
IF fridge_open_duration > threshold
→ fridge_left_open_risk

8. Balcony activity — watering plants (C)
Sensors:
Balcony PIR
Soil moisture sensor
Rule:
IF balcony_motion_detected
AND soil_moisture_increases
→ plant_watering