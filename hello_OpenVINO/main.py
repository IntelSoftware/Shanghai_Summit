from openvino import Core
def main():
    print("Hello from OpenVINO test!  I see these devices:")
    print(Core().available_devices)
if __name__ == "__main__":
    main()