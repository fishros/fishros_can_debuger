
import struct
import time

FRAME_CAN_RECV = 1
FRAME_CAN_SEND = 2
FRAME_CAN_INFO = 3
FRAME_CAN_SETRATE = 4

def decompose_byte(byte, decomposition_pattern):
    result = []
    index = 0

    for size in decomposition_pattern:
        bits = int(size)
        # print(bits, index)
        if index + bits <= 8:
            # Extract bits from low to high
            extracted_bits = (byte >> index) & ((1 << bits) - 1)
            result.append(extracted_bits)
            index += bits
        else:
            raise ValueError("Invalid decomposition pattern or byte size")

    return tuple(result)


def compose_byte(bit_values, composition_pattern):
    byte = 0
    index = 0

    for value, size in zip(bit_values, composition_pattern):
        bits = int(size)
        if value >= (1 << bits):
            raise ValueError("Bit value exceeds the specified bit size")
        byte |= (value & ((1 << bits) - 1)) << index
        index += bits

    if index > 8:
        raise ValueError("Composition pattern exceeds byte size")

    return byte



import struct  


class CanFrame():
    ID = FRAME_CAN_RECV
    def __init__(self,frame) -> None:
        parse_frame = struct.unpack('<BBBIB8sBB', frame)
        self.timestamp = time.time()
        extd,rtr,ss,self_,dlcncomp,nc1,nc2,nc3 = decompose_byte(parse_frame[2],"11111111")
        self.extd = extd # 扩展帧
        self.rtr = rtr # 远程帧
        self.id = parse_frame[3]
        self.len = parse_frame[4]
        self.data =  ' '.join(format(x, '02x') for x in list(parse_frame[5][:self.len]))
        self.checksum = parse_frame[1]
    

    def to_bytes(self):
        pass

    def __repr__(self):
        return f"[提示]收到CAN Frame: ID:{self.id} {self.len}->[{self.data}]"


class CanInfoReportFrame():
    ID = FRAME_CAN_INFO
    BUS_STATUS = {
        0:"已停止",
        1:"运行中",
        2:"已关闭",
        3:"已恢复",
    }
    def __init__(self,frame) -> None:
        # print(len(frame),frame,'\n', ' '.join(format(x, '02x') for x in list(frame)))
        parse_frame = struct.unpack('<BBHIIIIIIIIIIBB', frame)
        self.timestamp = time.time()
        # print(parse_frame)
        self.rate = parse_frame[2]
        self.bus_status = CanInfoReportFrame.BUS_STATUS[parse_frame[3]]
        self.msgs_to_tx =  parse_frame[4]
        self.msgs_to_rx =  parse_frame[5]
        self.tx_error_counter  = parse_frame[6]
        self.rx_error_counter  = parse_frame[7]
        self.tx_failed_count  = parse_frame[8]
        self.rx_missed_count  = parse_frame[9]
        self.rx_overrun_count  = parse_frame[10]
        self.arb_lost_count  = parse_frame[11]
        self.bus_error_count  = parse_frame[12]
    def to_bytes(self):
        pass

    def __repr__(self):
        return f"[提示]收到CAN Info rate:{self.rate} bus_status:{self.bus_status}  msgs_to_tx:{self.msgs_to_tx} msgs_to_rx:{self.msgs_to_rx} tx_error_counter:{self.tx_error_counter} rx_error_counter:{self.rx_error_counter} tx_failed_count:{self.tx_failed_count} rx_missed_count:{self.rx_missed_count} rx_overrun_count:{self.rx_overrun_count} arb_lost_count:{self.arb_lost_count} bus_error_count:{self.bus_error_count} ]"


class CanSetRateFrame():
    ID = FRAME_CAN_SETRATE
    def __init__(self,rate) -> None:
        self.rate = rate
    

    def to_bytes(self):
        content_data =  struct.pack('<BH',FRAME_CAN_SETRATE,self.rate)  

        checksum = sum(content_data) & 0xFF  # 使用按位与操作确保结果是8位
        content_data = struct.pack(f'{len(content_data)}sB',content_data,checksum)
        content_data = content_data.replace(b'\x50',b'\x50\x05').replace(b'\x5a',b'\x50\x0a')
        struct_format = f'<B{len(content_data)}sB'   
        packed_data = struct.pack(struct_format, 0x5A,content_data ,0x5A)  

        return packed_data

    def __repr__(self):
        return f"[提示]发送CAN Set Rate Frame: {self.rate}"



class CanSendFrame():
    ID = FRAME_CAN_SEND
    def __init__(self,id,extd,dlc,data) -> None:
        self.id = id
        self.extd = extd
        self.dlc = dlc
        self.data = data

    def to_bytes(self):
        flag = compose_byte((self.extd,0,0,0,0,0,0,0),"11111111")
        content_data =  struct.pack('<BBIB8s',FRAME_CAN_SEND,flag,self.id,self.dlc,self.data)  

        checksum = sum(content_data) & 0xFF  # 使用按位与操作确保结果是8位
        content_data = struct.pack(f'{len(content_data)}sB',content_data,checksum)
        content_data = content_data.replace(b'\x50',b'\x50\x05').replace(b'\x5a',b'\x50\x0a')
        struct_format = f'<B{len(content_data)}sB'   
        packed_data = struct.pack(struct_format, 0x5A,content_data ,0x5A)  


        # print(len(packed_data),packed_data,'\n', ' '.join(format(x, '02x') for x in list(packed_data)))

        return packed_data

    def __repr__(self):
        return f"[提示]发送CAN Set Rate Frame: {self.rate}"
