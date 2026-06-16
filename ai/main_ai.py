from ai.data_fetcher import get_latest_data
from ai.activity_engine import detect_activities, build_sensor_map
from ai.safety_engine import detect_risks
from ai.llm_reporter import generate_report


def run_ai_pipeline():
    raw_data = get_latest_data()

    # convert ThingsBoard format → simple events
    events = []
    for sensor, values in raw_data.items():
        latest = values[0]["value"]
        events.append({
            "sensor_id": sensor,
            "value": latest
        })

    sensor_map = build_sensor_map(events)
    activities = detect_activities(events)

    print("Detected activities:")
    print(activities)

    risks = detect_risks(sensor_map, activities)

    print("\nDetected risks:")
    if risks:
        for r in risks:
            print(f"  [{r['severity'].upper()}] {r['risk']}: {r['reason']}")
    else:
        print("  None")

    print("\nGenerating caregiver report...")
    report = generate_report(activities, risks)
    print("\n--- CAREGIVER REPORT ---")
    print(report)
    print("------------------------")


if __name__ == "__main__":
    run_ai_pipeline()