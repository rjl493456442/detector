from regularExtrator import regularExtrator

r = regularExtrator()
max = 0
min = 0
cnt = 0
if __name__ == "__main__":
    with open("test_data/2.log",'r') as file:
        while True:
            line = file.readline()
            if line:
                if line.find("AFCIDFQTMPositionCDHandler - Do proccess") != -1:
                    info = r.extra(line)
                    cnt = cnt + 1
                    print info[13]
                    if int(info[13]) > max:
                        max = int(info[13])
            else:
                break

    print str(max / 1000 / 1000)
    print cnt
