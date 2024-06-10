import serial
import time
import struct

# 打开串口
ser = serial.Serial('/dev/ttyUSB0', baudrate=1500000, timeout=10)


count = 0
start_time = time.time()
def frame_deal(frame):
    global count
    global start_time
    frame = frame.replace(b'\x50\x0a',b'\x5a').replace(b'\x50\x05',b'\x50')
    # print(len(frame),frame)
    count += 1
    # 检查帧长度是否符合要求
    if len(frame) != 18:
        print("Invalid frame length")
        print(len(frame),frame)
        return

    # 使用 struct 模块按照 C 结构体的定义解析数据
    parsed_frame = struct.unpack('<BBBIB8sBB', frame)
    if time.time() - start_time>1.0:
        start_time = time.time()
        print(f"{count} frame/s")
        count = 0
        print(parsed_frame)


def main():
    buffer = bytearray()
    while True:
        try:
            # 逐步读取数据
            buffer += ser.read(5)
            start = buffer.find(b'\x5A')
            end = buffer.find(b'\x5A', start + 2)

            # 处理找到的帧                                                                                                                                                                                                                                                   
            while start != -1 and end != -1:
                if end < start:
                    buffer = buffer[end + 1:]
                else:
                    frame = buffer[start:end + 1]
                    if len(frame) > 2:
                        frame_deal(frame)
                    buffer = buffer[end + 1:]
                start = buffer.find(b'\x5A')
                end = buffer.find(b'\x5A', start + 2)

        except Exception as e:
            print(f"Error: {e}")

# 调用主函数开始读取和输出帧
main()
