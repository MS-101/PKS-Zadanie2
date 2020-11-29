import client
import server
from threading import Thread
from tkinter import *
from tkinter import ttk

root = Tk()
connectionOpen = False

topFrame = Frame(root)
topFrame.pack(fill="x", padx=10, pady=5)

connectionConfigWrapper = LabelFrame(root)
connectionConfigWrapper.pack(fill="x", padx=10, pady=5)

clientIPLabel = Label(connectionConfigWrapper, text="Klient IP:")
clientIPLabel.grid(row=0, column=0, sticky=W, padx=10, pady=10)
clientPortLabel = Label(connectionConfigWrapper, text="Klient port:")
clientPortLabel.grid(row=1, column=0, sticky=W, padx=10, pady=10)

clientIPEntry = Entry(connectionConfigWrapper)
clientIPEntry.grid(row=0, column=1, pady=10)
clientPortEntry = Entry(connectionConfigWrapper)
clientPortEntry.grid(row=1, column=1, pady=10)

serverIPLabel = Label(connectionConfigWrapper, text="Server IP:")
serverIPLabel.grid(row=0, column=2, sticky=W, padx=10, pady=10)
serverPortLabel = Label(connectionConfigWrapper, text="Server port:")
serverPortLabel.grid(row=1, column=2, sticky=W, padx=10, pady=10)

serverIPEntry = Entry(connectionConfigWrapper)
serverIPEntry.grid(row=0, column=3, pady=10)
serverPortEntry = Entry(connectionConfigWrapper)
serverPortEntry.grid(row=1, column=3, pady=10)


def client_server_switch():
    new_state = clientOrServer.get()

    if new_state == "client":
        clientIPEntry.config(state="normal")
        clientPortEntry.config(state="normal")
    elif new_state == "server":
        clientIPEntry.config(state="disabled")
        clientPortEntry.config(state="disabled")


middleFrame = Frame(root)
middleFrame.pack(fill="x", padx=10, pady=5)

deviceState = StringVar()
deviceState.set("receiver")

deviceStateConfigLabel = Label(middleFrame, text="Stav komunikujúceho uzla:")
deviceStateConfigLabel.grid(row=0, column=0, sticky=W, padx=10)
receiverRadioBtn = Radiobutton(middleFrame, text="Prijímač", variable=deviceState, value="receiver", state="disabled")
receiverRadioBtn.grid(row=0, column=1, padx=10)
transmitterRadioBtn = Radiobutton(middleFrame, text="Vysielač", variable=deviceState, value="transmitter", state="disabled")
transmitterRadioBtn.grid(row=0, column=2, padx=10)

dataFrame = Frame(root)
dataFrame.pack(fill="x", padx=10, pady=5)

dataEntry = Entry(dataFrame, width=50, state="disabled")
dataEntry.grid(row=0, column=0)
textTransferBtn = Button(dataFrame, text="Poslať Text", state="disabled")
textTransferBtn.grid(row=0, column=1, padx=10)
fileTransferBtn = Button(dataFrame, text="Poslať Súbor", state="disabled")
fileTransferBtn.grid(row=0, column=2, padx=10)

clientOrServer = StringVar()
clientOrServer.set("client")


connectionConfigLabel = Label(topFrame, text="Konfigurácia pripojenia:")
connectionConfigLabel.grid(row=0, column=0, sticky=W, padx=10)
clientRadioBtn = Radiobutton(topFrame, text="Klient", variable=clientOrServer, value="client", command=client_server_switch)
clientRadioBtn.grid(row=0, column=1, padx=10)
serverRadioBtn = Radiobutton(topFrame, text="Server", variable=clientOrServer, value="server", command=client_server_switch)
serverRadioBtn.grid(row=0, column=2, padx=10)


def open_close_connection():
    global connectionOpen

    if connectionOpen is False:
        connectionOpen = True

        clientRadioBtn.config(state="disabled")
        serverRadioBtn.config(state="disabled")

        clientIPEntry.config(state="readonly")
        clientPortEntry.config(state="readonly")
        serverIPEntry.config(state="readonly")
        serverPortEntry.config(state="readonly")

        dataEntry.config(state="normal")
        textTransferBtn.config(state="normal")
        fileTransferBtn.config(state="normal")
        receiverRadioBtn.config(state="normal")
        transmitterRadioBtn.config(state="normal")

        connectionStartOrEndBtn.config(text="Zatvor Spojenie")
    else:
        connectionOpen = False

        clientRadioBtn.config(state="normal")
        serverRadioBtn.config(state="normal")

        if clientOrServer.get() == "client":
            clientIPEntry.config(state="normal")
            clientPortEntry.config(state="normal")
        else:
            clientIPEntry.config(state="disabled")
            clientPortEntry.config(state="disabled")
        serverIPEntry.config(state="normal")
        serverPortEntry.config(state="normal")

        dataEntry.config(state="disabled")
        textTransferBtn.config(state="disabled")
        fileTransferBtn.config(state="disabled")
        receiverRadioBtn.config(state="disabled")
        transmitterRadioBtn.config(state="disabled")

        connectionStartOrEndBtn.config(text="Otvor Spojenie")


connectionStartOrEndBtn = Button(topFrame, text="Otvor Spojenie", command=open_close_connection)
connectionStartOrEndBtn.grid(row=0, column=3)


messageLogWrapper = LabelFrame(root)
messageLogWrapper.pack(fill="both", expand="yes", padx=10, pady=5)

messageLogCanvas = Canvas(messageLogWrapper)
messageLogCanvas.pack(side=LEFT)

yScrollbar = ttk.Scrollbar(messageLogWrapper, orient="vertical", command=messageLogCanvas.yview)
yScrollbar.pack(side=RIGHT, fill="y")

messageLogCanvas.configure(yscrollcommand=yScrollbar.set)

messageLogCanvas.bind('<Configure>', lambda e: messageLogCanvas.configure(scrollregion=messageLogCanvas.bbox("all")))

messageLogFrame = Frame(messageLogCanvas)
messageLogCanvas.create_window((0, 0), window=messageLogFrame, anchor="nw")

root.geometry("500x400")
root.resizable(False, False)
root.title("Svab_PKS_zadanie2")
root.mainloop()

"""
serverAddress = ("localhost", 12345)

server.set_server_address(serverAddress)
client.set_server_address(serverAddress)

Thread(target=server.open_socket).start()
client.send_to_server("ahoj")
Thread(target=client.open_socket).start()
"""
