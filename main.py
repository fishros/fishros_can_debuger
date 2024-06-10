from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QHeaderView, QComboBox, QPushButton, QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QTimer, Qt
import time
import signal
import sys
from queue import Queue
from devices.device_helper import DeviceHelper
from can.can_helper import CanHelper
from can.canframe import *
import datetime
import os

CURRENT_DIR = os.path.dirname(__file__)
os.environ['FISHBOT_CURRENT_DIR'] = CURRENT_DIR

class CustomComboBox(QWidget):
    def __init__(self, parent=None):
        super(CustomComboBox, self).__init__(parent)
        self.layout = QVBoxLayout()
        self.combo = QComboBox()
        self.combo.addItems(["标准帧", "扩展帧"])
        self.layout.addWidget(self.combo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def is_extd(self):
        return self.combo.currentIndex() == 1

class CustomButton(QWidget):
    def __init__(self, parent=None, form=None, row_index=0, can_helper=None):
        super(CustomButton, self).__init__(parent)
        self.form = form
        self.row_index = row_index
        self.can_helper = can_helper

        self.layout = QVBoxLayout()
        self.button = QPushButton("发送")
        self.layout.addWidget(self.button)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.button.clicked.connect(self.on_click)

    def on_click(self):
        # 从form和row_index获取数据，然后组装成CANFrame，通过can_helper发送出去
        table_model = self.form.tableViewSendCan.model()
        frame_id = table_model.item(self.row_index, 0).text()
        frame_type_widget = self.form.tableViewSendCan.indexWidget(table_model.index(self.row_index, 1))
        is_extd = frame_type_widget.is_extd()
        frame_len = int(table_model.item(self.row_index, 2).text())
        frame_data = table_model.item(self.row_index, 3).text().split()

        id = int(frame_id, 16)
        extd = is_extd
        len = frame_len
        data = bytes(int(x, 16) for x in frame_data)
        frame = CanSendFrame(id,extd,len,data)

        if self.can_helper.write_frame(frame):
            # print(f'Send success!')
            pass
        else:
            print('Send error!')

class FishCanDebuger:
    def __init__(self) -> None:
        Form, Window = uic.loadUiType(f"{CURRENT_DIR}/ui/main.ui")
        self.app = QApplication([])
        self.window = Window()
        self.form = Form()
        self.form.setupUi(self.window)

        self.frame_queue = Queue()
        self.log_queue = Queue()
        self.log_text = ""
        self._timer = QTimer()
        self._timer.timeout.connect(self.handleTimeoutLog)
        self._timer.setInterval(2)
        self._timer.start()
        self.second_update = False

        self.initialize_table()
        self.device_helper = DeviceHelper(self.put_log)
        self.can_helper = CanHelper(self.put_log)

        self.form.action_fishros.triggered.connect(self.click_about)
        self.form.action_shop.triggered.connect(self.click_shop)
        self.form.pushButtonDeviceFresh.clicked.connect(self.clicked_push_button_device_fresh)
        self.form.pushButtonDeviceOpen.clicked.connect(self.clicked_push_button_device_open)
        self.form.pushButtonDeviceClose.clicked.connect(self.clicked_push_button_device_close)
        self.form.pushButtonClearScreen.clicked.connect(self.clicked_push_button_clear_screen)
        self.form.pushButtonSetRate.clicked.connect(self.clicked_push_button_set_rate)
        self.form.pushButtonAddSend.clicked.connect(self.clicked_push_button_add_send)

        self.form.checkBoxAutoScoll.stateChanged.connect(self.checkbox_auto_scoll)
        self.auto_scoll = False

        signal.signal(signal.SIGINT, self.signal_handler)

        self.form.pushButtonDeviceOpen.setDisabled(False)
        self.form.pushButtonDeviceClose.setDisabled(True)
        self.clicked_push_button_device_fresh()

        self.recv_lastupdate_time = time.time()
        self.recv_count = 0
        self.send_lastupdate_time = time.time()
        self.send_count = 0

        self.form.commonBoxFilterID.setDisabled(True)
        self.form.lineEditFilterID.setDisabled(True)
        self.form.commonBoxMaxFrameCount.setDisabled(True)

        self.rate2index_map = {100: 0, 125: 1, 250: 2, 500: 3, 800: 4, 1000: 5}
        self.update_rate = False

    def checkbox_auto_scoll(self, state):
        self.auto_scoll = self.form.checkBoxAutoScoll.isChecked()

    def clicked_push_button_set_rate(self):
        rate = int(self.form.commonBoxRateSet.currentText())
        frame = CanSetRateFrame(rate)
        self.can_helper.write_frame(frame)

    def clicked_push_button_clear_screen(self):
        self.tableModel.removeRows(0, self.tableModel.rowCount())

    def get_current_device(self):
        device_str = self.form.commonBoxDevices.currentText()
        device = None
        if len(device_str) == 0:
            self.put_log(f"[错误]检测当前设备为空,请重新选择设备！")
        else:
            device = self.device_helper.get_device(device_str)
        return device

    def frame_callback(self, frame):
        if frame.ID == FRAME_CAN_RECV:
            self.frame_queue.put(frame)
        if frame.ID == FRAME_CAN_INFO:
            self.frame_queue.put(frame)

    def clicked_push_button_device_open(self):
        device = self.get_current_device()
        if device:
            self.can_helper.close()
            self.can_helper.set_device(device)
            self.can_helper.open(self.frame_callback)
            self.update_rate = True
            self.form.pushButtonDeviceOpen.setDisabled(True)
            self.form.pushButtonDeviceClose.setDisabled(False)

    def clicked_push_button_device_close(self):
        self.can_helper.close(log=True)
        self.form.pushButtonDeviceOpen.setDisabled(False)
        self.form.pushButtonDeviceClose.setDisabled(True)

    def clicked_push_button_device_fresh(self):
        devices = self.device_helper.get_all_devices()
        self.update_log(f"[提示]获取到当前系统设备 {str(devices)}")
        self.form.commonBoxDevices.clear()
        self.form.commonBoxDevices.addItems(devices.keys())
        self.form.commonBoxDevices.setCurrentIndex(0)

    def initialize_table(self):
        self.tableModel = QStandardItemModel()
        headers = ["时间", "方向", "ID", "帧类型", "长度", "数据"]
        self.tableModel.setHorizontalHeaderLabels(headers)

        self.form.tableViewCANFrame.setModel(self.tableModel)
        header = self.form.tableViewCANFrame.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.form.tableViewCANFrame.setColumnWidth(0, 180)
        self.form.tableViewCANFrame.setColumnWidth(1, 60)
        self.form.tableViewCANFrame.setColumnWidth(2, 100)
        self.form.tableViewCANFrame.setColumnWidth(3, 80)
        self.form.tableViewCANFrame.setColumnWidth(4, 50)
        self.form.tableViewCANFrame.setColumnWidth(5, 300)

        self.tableSendCanModel = QStandardItemModel()
        headers = ["ID", "帧类型", "长度", "数据", "发送"]
        self.tableSendCanModel.setHorizontalHeaderLabels(headers)
        self.form.tableViewSendCan.setModel(self.tableSendCanModel)
        header = self.form.tableViewSendCan.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.form.tableViewSendCan.setColumnWidth(0, 100)
        self.form.tableViewSendCan.setColumnWidth(1, 100)
        self.form.tableViewSendCan.setColumnWidth(2, 60)
        self.form.tableViewSendCan.setColumnWidth(3, 100)
        self.form.tableViewSendCan.setColumnWidth(4, 80)

    def clicked_push_button_add_send(self):
        item_id = QStandardItem("01")
        item_type = QStandardItem()
        item_len = QStandardItem("8")
        item_data = QStandardItem("00 00 00 00 00 00 00 00")
        item_send_btn = QStandardItem()

        self.tableSendCanModel.appendRow([
            item_id,
            item_type,
            item_len,
            item_data,
            item_send_btn
        ])

        combo_box = CustomComboBox()
        send_button = CustomButton(form=self.form, row_index=self.tableSendCanModel.rowCount() - 1, can_helper=self.can_helper)

        self.form.tableViewSendCan.setIndexWidget(self.tableSendCanModel.index(self.tableSendCanModel.rowCount() - 1, 1), combo_box)
        self.form.tableViewSendCan.setIndexWidget(self.tableSendCanModel.index(self.tableSendCanModel.rowCount() - 1, 4), send_button)

    def signal_handler(self, sig, frame):
        print("Exiting...")
        self.app.quit()
        sys.exit(0)

    def click_about(self):
        Form, Window = uic.loadUiType(f"{CURRENT_DIR}/ui/about.ui")
        window = Window()
        form = Form()
        form.setupUi(window)
        window.show()
        window.exec()

    def click_shop(self):
        Form, Window = uic.loadUiType(f"{CURRENT_DIR}/ui/taobao.ui")
        window = Window()
        form = Form()
        form.setupUi(window)
        window.show()
        window.exec()

    def show(self):
        self.window.show()
        self.app.exec()

    def put_log(self, log):
        self.log_queue.put(log)

    def update_log(self, text):
        self.log_text = str(time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime())) + " > " + str(text)
        print(self.log_text)
        self.form.textEditSystemLog.append(self.log_text)
        scrollbar = self.form.textEditSystemLog.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_frame(self, frame):
        dt_object = datetime.datetime.fromtimestamp(frame.timestamp)
        formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Strip the last three digits to get milliseconds
        timestamp_item = QStandardItem(formatted_time)
        direction_item = QStandardItem("接收" if frame.ID == FRAME_CAN_RECV else "发送")
        can_id_item = QStandardItem(f"{hex(frame.id)}")
        frame_type_item = QStandardItem("标准帧" if frame.extd else "数据帧")
        frame_length_item = QStandardItem(str(frame.len))
        frame_data_item = QStandardItem(frame.data)

        self.tableModel.appendRow([
            timestamp_item,
            direction_item,
            can_id_item,
            frame_type_item,
            frame_length_item,
            frame_data_item
        ])

        if self.auto_scoll:
            index = self.tableModel.index(self.tableModel.rowCount() - 1, 0)
            QTimer.singleShot(50, lambda: self.form.tableViewCANFrame.scrollTo(index))

        if frame.ID == FRAME_CAN_RECV:
            self.recv_count += 1
        else:
            self.send_count += 1

    def handleTimeoutLog(self):
        while self.log_queue.qsize() > 0:
            text = self.log_queue.get()
            if len(text.strip()) > 0:
                self.update_log(text)

        while self.frame_queue.qsize() > 0:
            frame = self.frame_queue.get()
            if frame.ID == FRAME_CAN_INFO:
                if self.update_rate:
                    self.update_rate = False
                    current_rate = int(self.form.commonBoxRateSet.currentText())
                    if current_rate != frame.rate:
                        self.form.commonBoxRateSet.setCurrentIndex(self.rate2index_map[frame.rate])
            else:
                self.update_frame(frame)

        if time.time() - self.recv_lastupdate_time > 1.0:
            self.recv_lastupdate_time = time.time()
            self.form.labelRecvRate.setText(f'{self.recv_count}')
            self.recv_count = 0

        if time.time() - self.send_lastupdate_time > 1.0:
            self.send_lastupdate_time = time.time()
            self.form.labelSendRate.setText(f'{self.send_count}')
            self.send_count = 0

if __name__ == "__main__":
    debug = FishCanDebuger()
    debug.update_log("FishROS CAN Debuger 已启动。")
    debug.show()
