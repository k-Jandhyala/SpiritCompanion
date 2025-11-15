import time

FocusTime = int(input("Enter the amount of time you want to focus for in seconds: "))
RestTime=int(input("Enter the amount of time you want rest for in seconds: "))
RepeatTime=int(input("Enter the amount of time you want this to repeat in seconds: "))


for i in range(0,int(FocusTime/RepeatTime)):
    print("Your Focus Period has started!")
    FocusCount=0
    while True:
        time.sleep(1)
        FocusCount+=1
        if FocusCount == (RepeatTime) - (int(RepeatTime/6)):
            print(round(FocusCount/60,2), "Minutes have passed...")
            break

    time.sleep(int(RepeatTime/6))
    print("Your focus period is over!")
    print("Now starts your well deserved", RestTime, " minutes of rest period")


    RestCount=0
    while True:
        time.sleep(1)
        RestCount+=1
        if RestCount == (RestTime) - (int(RestTime/6)):
            print(round(RestCount/60,2), "Minutes have passed...")
            break

    time.sleep(int(RestTime/6))
    print("Your rest period is over!")
    print()