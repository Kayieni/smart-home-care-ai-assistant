from simulator.scenarios import run_normal, run_decline, run_hazard
from simulator.timeline import run_timeline, TIMELINE_NORMAL, TIMELINE_DECLINE, TIMELINE_HAZARD

if __name__ == "__main__":
    print("Choose mode:")
    print("1 - Instant scenario (original)")
    print("2 - Full-day timeline simulation (new)")
    mode = input("> ").strip()

    if mode == "1":
        print("\nChoose scenario:")
        print("1 - Normal")
        print("2 - Decline")
        print("3 - Hazard")
        choice = input("> ").strip()
        if choice == "1":
            run_normal()
        elif choice == "2":
            run_decline()
        elif choice == "3":
            run_hazard()

    elif mode == "2":
        print("\nChoose scenario:")
        print("1 - Normal")
        print("2 - Decline")
        print("3 - Hazard")
        choice = input("> ").strip()
        if choice == "1":
            run_timeline(TIMELINE_NORMAL, "Normal Day")
        elif choice == "2":
            run_timeline(TIMELINE_DECLINE, "Decline Day")
        elif choice == "3":
            run_timeline(TIMELINE_HAZARD, "Hazard Day")
