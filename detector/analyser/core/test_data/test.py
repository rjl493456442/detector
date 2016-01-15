cnt = 0
def function():
    global cnt
    with open("2.log", 'r') as f:
        while cnt <= 10:
            line = f.readline()
            print line
            cnt = cnt + 1

if __name__ == "__main__":
    function()
