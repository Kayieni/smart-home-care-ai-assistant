from simulator.scenarios import run_normal, run_decline, run_hazard

if __name__ == "__main__":
    print("Choose scenario:")
    print("1 - Normal")
    print("2 - Decline")
    print("3 - Hazard")

    choice = input("> ")

    if choice == "1":
        run_normal()
    elif choice == "2":
        run_decline()
    elif choice == "3":
        run_hazard()