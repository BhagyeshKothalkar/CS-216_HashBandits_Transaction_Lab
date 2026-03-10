from legacy import run_legacy
from segwit import run_segwit
from compare import run_compare

def main():
    print("Choose Transaction Mode:")
    print("Press 1 for Legacy")
    print("Press 2 for Segwit")
    print("Press 3 for Comparative Analysis")
    print("Press 4 to Exit")
    t_mode = int(input("Mode: "))
    while t_mode != 4:
        if t_mode == 1:
            print("Executing Legacy Transaction")
            run_legacy()
            break
        elif t_mode == 2:
            print("Executing SegWit Transaction")
            run_segwit()
            break
        elif t_mode == 3:
            print("Executing Comparative Analysis")
            run_compare()
            break
        else:
            print(f"Please Try Again using a valid mode")
            t_mode = int(input("Mode: "))

if __name__ == "__main__":
    main()