import serial
import threading
import struct
from can.canframe import CanFrame,CanInfoReportFrame
import time

class CanHelper():
    def __init__(self,logger) -> None:
        self.logger = logger
        self.frame_callback = None
        self.device_event_callback = None
        self.serial_thread = None
        self.device = None
        self.frame_parse = {
            CanFrame.ID: CanFrame,
            CanInfoReportFrame.ID: CanInfoReportFrame
        }

    def set_device(self,device):
        self.device = device

    def frame_deal(self,frame):
        try:
            frame = frame.replace(b'\x50\x0a',b'\x5a').replace(b'\x50\x05',b'\x50')
            frame_id = int(frame[1])
            if frame_id in self.frame_parse.keys():
                can_frame = self.frame_parse[frame_id](frame)
                self.logger(f"{can_frame}")
                if self.frame_callback:
                    self.frame_callback(can_frame)
            else:
                print(frame)
        except Exception as e:
            print(e)

    def serial_read_thread(self):
        try:
            buffer = bytearray()
            while self.runing:
                try:
                    # 逐步读取数据
                    buffer += self.serial.read(5)
                    start = buffer.find(b'\x5A')
                    end = buffer.find(b'\x5A', start + 2)

                    # 处理找到的帧                                                                                                                                                                                                                                                   
                    while start != -1 and end != -1:
                        if end < start:
                            buffer = buffer[end + 1:]
                        else:
                            frame = buffer[start:end + 1]
                            if len(frame) > 2:
                                self.frame_deal(frame)
                            buffer = buffer[end + 1:]
                        start = buffer.find(b'\x5A')
                        end = buffer.find(b'\x5A', start + 2)
                except Exception as e:
                    print(f"Error: {e.with_traceback()}")
        except Exception as e:
            print(e.with_traceback())

    def open(self,frame_callback=None):
        baudrate=1500000
        self.frame_callback = frame_callback
        try:
            self.close()
            self.serial = serial.Serial(port=self.device.device_name,baudrate=baudrate,timeout=0.01)
            self.serial_thread = threading.Thread(target=self.serial_read_thread)
            self.runing = True
        except Exception as e:
            self.logger(f'[提示]设备{self.device.device_name}打开失:{e.with_traceback()}')
            return

        self.serial_thread.start()
        self.logger(f'[提示]设备{self.device.device_name}已打开')

    def close(self,log=False):
        try:
            self.runing = False
            if self.serial_thread:
                while self.serial_thread.is_alive():
                    time.sleep(0.001)
                    # self.logger('thread is runing')
                    # print('thread is runing')
            if self.serial:
                self.serial.close()
        except:
            pass

        if self.device and log:
            self.logger(f'[提示]设备{self.device.device_name}已关闭')
     

    def event_callback(self,device_event_callback):
        self.event_callback = device_event_callback

    def write_frame(self,frame):
        self.logger(f"[提示]发送帧：{frame}")
        try:
            if self.serial:
                self.serial.write(frame.to_bytes())
                self.logger(f"[提示]发送帧 {frame} 成功!")
                return True
        except:
            self.logger(f"[提示]发送帧 {frame} 失败!")
            pass
        return False

if __name__=='__main__':
    def logger(msg):
        print(msg)

    class Device():
        device_name='/dev/ttyUSB0'

    can = CanHelper(logger)
    can.set_device(Device())
    can.open()