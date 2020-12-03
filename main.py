import threading
from tkinter import *
from tkinter import ttk

import client
import server

maxFragmentSize = 65492
portMin = 49152
portMax = 65535


def set_entry(entry, text):
    original_state = entry["state"]

    if original_state != "normal":
        entry.config(state="normal")

    entry.delete("0", "end")
    entry.insert("0", text)

    if original_state != "normal":
        entry.config(state=original_state)


class MainGUI:
    def send_message(self, message):
        Label(self.messageLogFrame, text=message).pack()

    def set_client_address(self, client_ip, client_port):
        set_entry(self.clientIPEntry, client_ip)
        set_entry(self.clientPortEntry, client_port)

    def press_send_file(self):
        file_path = self.fileTransferEntry.get()
        fragment_size = int(self.fragmentSizeEntry.get())

        if fragment_size > maxFragmentSize:
            self.send_message("MAX FRAGMENT SIZE IS " + str(maxFragmentSize) + "!")
            return

        if self.clientOrServer.get() == "client":
            threading.Thread(target=client.send_to_server_file, args=(file_path, fragment_size)).start()
        else:
            threading.Thread(target=server.send_to_client_file, args=(file_path, fragment_size)).start()

    def press_send_text(self):
        text = self.textTransferEntry.get()
        fragment_size = int(self.fragmentSizeEntry.get())

        if fragment_size > maxFragmentSize:
            self.send_message("MAX FRAGMENT SIZE IS " + str(maxFragmentSize) + "!")
            return

        if self.clientOrServer.get() == "client":
            threading.Thread(target=client.send_to_server_text, args=(text, fragment_size)).start()
        else:
            threading.Thread(target=server.send_to_client_text, args=(text, fragment_size)).start()

    def client_server_switch(self):
        new_state = self.clientOrServer.get()

        if new_state == "client":
            self.set_client_buttons()
        elif new_state == "server":
            self.set_server_buttons()

    def transmitter_receiver_switch(self):
        new_state = self.deviceState.get()

        if new_state == "receiver":
            self.set_receiver_buttons()
        elif new_state == "transmitter":
            self.set_transmitter_buttons()

    def open_close_connection(self):
        if self.connectionOpen is False:
            if self.clientOrServer.get() == "server":
                if int(self.serverPortEntry.get()) < portMin or int(self.serverPortEntry.get()) > portMax:
                    self.send_message("port must be in range: " + str(portMin) + "-" + str(portMax))
                    return

            if self.clientOrServer.get() == "client":
                if int(self.serverPortEntry.get()) < portMin or int(self.serverPortEntry.get()) > portMax \
                        or int(self.clientPortEntry.get()) < portMin or int(self.clientPortEntry.get()) > portMax:
                    self.send_message("port must be in range: " + str(portMin) + "-" + str(portMax))
                    return

            self.connectionOpen = True

            self.set_open_connection_buttons()

            if self.clientOrServer.get() == "server":
                self.set_client_address("", "")

                server.set_server_address(self.serverIPEntry.get(), int(self.serverPortEntry.get()))
                server.bind_socket()

                server.cur_sqn = 0

                threading.Thread(target=server.start_server_listener).start()
            else:
                client.set_client_address(self.clientIPEntry.get(), int(self.clientPortEntry.get()))
                client.set_server_address(self.serverIPEntry.get(), int(self.serverPortEntry.get()))
                client.bind_socket()

                client.cur_sqn = 0

                threading.Thread(target=client.start_client_listener).start()
                threading.Thread(target=client.send_to_server_syn).start()
        else:
            self.connectionOpen = False

            self.set_closed_connection_buttons()

            if self.clientOrServer.get() == "server":
                if server.updateReceiverOn is True:
                    threading.Thread(target=server.send_to_client_fin).start()
                else:
                    threading.Thread(target=server.close_connection).start()
            else:
                if client.updateSenderOn is True:
                    threading.Thread(target=client.send_to_server_fin).start()
                else:
                    threading.Thread(target=client.close_connection).start()

    def set_server_buttons(self):
        self.clientIPEntry.config(state="disabled")
        self.clientPortEntry.config(state="disabled")

    def set_client_buttons(self):
        self.clientIPEntry.config(state="normal")
        self.clientPortEntry.config(state="normal")

    def set_open_connection_buttons(self):
        self.clientRadioBtn.config(state="disabled")
        self.serverRadioBtn.config(state="disabled")

        self.clientIPEntry.config(state="disabled")
        self.clientPortEntry.config(state="disabled")
        self.serverIPEntry.config(state="disabled")
        self.serverPortEntry.config(state="disabled")

        if self.deviceState.get() == "transmitter":
            self.set_transmitter_buttons()
        else:
            self.set_receiver_buttons()
        self.receiverRadioBtn.config(state="normal")
        self.transmitterRadioBtn.config(state="normal")

        self.connectionStartOrEndBtn.config(text="Zatvor Spojenie")

    def set_closed_connection_buttons(self):
        self.clientRadioBtn.config(state="normal")
        self.serverRadioBtn.config(state="normal")

        if self.clientOrServer.get() == "client":
            self.clientIPEntry.config(state="normal")
            self.clientPortEntry.config(state="normal")
        else:
            self.clientIPEntry.config(state="disabled")
            self.clientPortEntry.config(state="disabled")
        self.serverIPEntry.config(state="normal")
        self.serverPortEntry.config(state="normal")

        self.fileReceiveEntry.config(state="disabled")
        self.fragmentSizeEntry.config(state="disabled")
        self.textTransferEntry.config(state="disabled")
        self.fileTransferEntry.config(state="disabled")
        self.textTransferBtn.config(state="disabled")
        self.fileTransferBtn.config(state="disabled")
        self.receiverRadioBtn.config(state="disabled")
        self.transmitterRadioBtn.config(state="disabled")

        self.connectionStartOrEndBtn.config(text="Otvor Spojenie")

    def set_receiver_buttons(self):
        self.fileReceiveEntry.config(state="normal")
        self.fragmentSizeEntry.config(state="disabled")
        self.fileTransferEntry.config(state="disabled")
        self.textTransferEntry.config(state="disabled")
        self.textTransferBtn.config(state="disabled")
        self.fileTransferBtn.config(state="disabled")
        self.standardBtn.config(state="disabled")
        self.extraBtn.config(state="disabled")

    def set_transmitter_buttons(self):
        self.fileReceiveEntry.config(state="disabled")
        self.fragmentSizeEntry.config(state="normal")
        self.fileTransferEntry.config(state="normal")
        self.textTransferEntry.config(state="normal")
        self.textTransferBtn.config(state="normal")
        self.fileTransferBtn.config(state="normal")
        self.standardBtn.config(state="normal")
        self.extraBtn.config(state="normal")

    def __init__(self):
        self.root = Tk()
        self.connectionOpen = False

        self.topFrame = Frame(self.root)
        self.topFrame.pack(fill="x", padx=10, pady=5)

        self.connectionConfigWrapper = LabelFrame(self.root)
        self.connectionConfigWrapper.pack(fill="x", padx=10, pady=5)

        self.clientIPLabel = Label(self.connectionConfigWrapper, text="Klient IP:")
        self.clientIPLabel.grid(row=0, column=0, sticky=W, padx=10, pady=10)
        self.clientPortLabel = Label(self.connectionConfigWrapper, text="Klient port:")
        self.clientPortLabel.grid(row=1, column=0, sticky=W, padx=10, pady=10)

        self.clientIPEntry = Entry(self.connectionConfigWrapper, width=30)
        self.clientIPEntry.grid(row=0, column=1, pady=10)
        set_entry(self.clientIPEntry, "127.0.0.1")
        self.clientPortEntry = Entry(self.connectionConfigWrapper, width=30)
        self.clientPortEntry.grid(row=1, column=1, pady=10)
        set_entry(self.clientPortEntry, "50000")

        self.serverIPLabel = Label(self.connectionConfigWrapper, text="Server IP:")
        self.serverIPLabel.grid(row=0, column=2, sticky=W, padx=10, pady=10)
        self.serverPortLabel = Label(self.connectionConfigWrapper, text="Server port:")
        self.serverPortLabel.grid(row=1, column=2, sticky=W, padx=10, pady=10)

        self.serverIPEntry = Entry(self.connectionConfigWrapper, width=30)
        self.serverIPEntry.grid(row=0, column=3, pady=10)
        set_entry(self.serverIPEntry, "127.0.0.2")
        self.serverPortEntry = Entry(self.connectionConfigWrapper, width=30)
        self.serverPortEntry.grid(row=1, column=3, pady=10)
        set_entry(self.serverPortEntry, "50001")

        self.deviceStateFrame = Frame(self.root)
        self.deviceStateFrame.pack(fill="x", padx=10, pady=5)

        self.deviceState = StringVar()
        self.deviceState.set("receiver")

        self.deviceStateConfigLabel = Label(self.deviceStateFrame, text="Stav komunikujúceho uzla:")
        self.deviceStateConfigLabel.grid(row=0, column=0, sticky=W, padx=10)
        self.receiverRadioBtn = Radiobutton(self.deviceStateFrame, text="Prijímač", variable=self.deviceState,
                                            value="receiver", state="disabled",
                                            command=self.transmitter_receiver_switch)
        self.receiverRadioBtn.grid(row=0, column=1, padx=10)
        self.transmitterRadioBtn = Radiobutton(self.deviceStateFrame, text="Vysielač", variable=self.deviceState,
                                               value="transmitter", state="disabled",
                                               command=self.transmitter_receiver_switch)
        self.transmitterRadioBtn.grid(row=0, column=2, padx=10)

        self.fileReceiveFrame = Frame(self.root)
        self.fileReceiveFrame.pack(fill="x", padx=10, pady=5)

        self.fileReceiveLabel = Label(self.fileReceiveFrame, text="Adresár prijatých súborov:")
        self.fileReceiveLabel.grid(row=0, column=0, padx=10)
        self.fileReceiveEntry = Entry(self.fileReceiveFrame, width=60, state="disabled")
        set_entry(self.fileReceiveEntry, "Receiver")
        self.fileReceiveEntry.grid(row=0, column=1, padx=10)

        self.fragmentsFrame = Frame(self.root)
        self.fragmentsFrame.pack(fill="x", padx=10, pady=5)

        self.fragmentSizeLabel = Label(self.fragmentsFrame, text="Veľkosť fragmentov:")
        self.fragmentSizeLabel.grid(row=0, column=0, padx=10)
        self.fragmentSizeEntry = Entry(self.fragmentsFrame, width=20, state="disabled")
        set_entry(self.fragmentSizeEntry, "4")
        self.fragmentSizeEntry.grid(row=0, column=1, padx=10)
        self.fragmentSizeWarning = Label(self.fragmentsFrame, text="(Maximálna veľkosť fragmentov je " + str(maxFragmentSize) + " B)")
        self.fragmentSizeWarning.grid(row=0, column=2, padx=10)

        self.textTransferFrame = Frame(self.root)
        self.textTransferFrame.pack(fill="x", padx=10, pady=5)

        self.textTransferEntry = Entry(self.textTransferFrame, width=70, state="disabled")
        set_entry(self.textTransferEntry, "Hello world!")
        self.textTransferEntry.grid(row=0, column=0)
        self.textTransferBtn = Button(self.textTransferFrame, text="Poslať Text", state="disabled",
                                      command=self.press_send_text, width=15)
        self.textTransferBtn.grid(row=0, column=1, padx=10)

        self.fileTransferFrame = Frame(self.root)
        self.fileTransferFrame.pack(fill="x", padx=10, pady=5)

        self.fileTransferEntry = Entry(self.fileTransferFrame, width=70, state="disabled")
        self.fileTransferEntry.grid(row=0, column=0)
        set_entry(self.fileTransferEntry, "Transmitter/test1.txt")
        self.fileTransferBtn = Button(self.fileTransferFrame, text="Poslať Súbor", state="disabled",
                                      command=self.press_send_file, width=15)
        self.fileTransferBtn.grid(row=0, column=2, padx=10)

        self.clientOrServer = StringVar()
        self.clientOrServer.set("client")

        self.connectionConfigLabel = Label(self.topFrame, text="Konfigurácia pripojenia:")
        self.connectionConfigLabel.grid(row=0, column=0, sticky=W, padx=10)
        self.clientRadioBtn = Radiobutton(self.topFrame, text="Klient", variable=self.clientOrServer, value="client",
                                          command=self.client_server_switch)
        self.clientRadioBtn.grid(row=0, column=1, padx=10)
        self.serverRadioBtn = Radiobutton(self.topFrame, text="Server", variable=self.clientOrServer, value="server",
                                          command=self.client_server_switch)
        self.serverRadioBtn.grid(row=0, column=2, padx=10)

        self.connectionStartOrEndBtn = Button(self.topFrame, text="Otvor Spojenie", command=self.open_close_connection)
        self.connectionStartOrEndBtn.grid(row=0, column=3)

        self.extraFrame = Frame(self.root)
        self.extraFrame.pack(fill="x", padx=10, pady=5)

        self.standardOrExtra = StringVar()
        self.standardOrExtra.set("standard")

        self.standardOrExtraLabel = Label(self.extraFrame, text="Prepni medzi finálnym riešením a doimplementáciou:")
        self.standardOrExtraLabel.grid(row=0, column=0, sticky=W, padx=10)
        self.standardBtn = Radiobutton(self.extraFrame, text="Classic", variable=self.standardOrExtra, value="standard",
                                       state="disabled")
        self.standardBtn.grid(row=0, column=1, padx=10)
        self.extraBtn = Radiobutton(self.extraFrame, text="Doimplementácia", variable=self.standardOrExtra,
                                    value="extra", state="disabled")
        self.extraBtn.grid(row=0, column=2, padx=10)

        self.messageLogWrapper = LabelFrame(self.root)
        self.messageLogWrapper.pack(fill="both", expand="yes", padx=10, pady=5)

        self.messageLogCanvas = Canvas(self.messageLogWrapper, width=600)
        self.messageLogCanvas.pack(side=LEFT)

        self.yScrollbar = ttk.Scrollbar(self.messageLogWrapper, orient="vertical", command=self.messageLogCanvas.yview)
        self.yScrollbar.pack(side=RIGHT, fill="y")

        self.messageLogCanvas.configure(yscrollcommand=self.yScrollbar.set)

        self.messageLogCanvas.bind('<Configure>', lambda e: self.messageLogCanvas.configure(scrollregion=self.messageLogCanvas.bbox("all")))

        self.messageLogFrame = Frame(self.messageLogCanvas)
        self.messageLogCanvas.create_window((0, 0), window=self.messageLogFrame, anchor="nw")

        self.root.geometry("600x500")
        self.root.resizable(False, False)
        self.root.title("Svab_PKS_zadanie2")

        server.set_gui(self)
        client.set_gui(self)

        self.root.mainloop()


my_main_gui = MainGUI()
