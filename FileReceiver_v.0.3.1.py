#!/usr/bin/env python
#-*- coding: utf-8 -*-
#ver 16/01/2024

import socket
import pickle
import sys
import os
import wx
from wx.adv import SplashScreen as SplashScreen
import wx.aui # for throbber
import wx.lib.throbber # for throbber
from pubsub import pub
import threading
from threading import Thread
import time
import datetime  
from datetime import datetime, timedelta
import locale
import queue
#import string
#import struct #for trnsiving bytes
import hashlib #for md5

#===========================================================================
# Main Window
class MainWindow(wx.Frame):

    # задаем конструктор
    def __init__(self):
        try:
            #self.SizeWin = (250, 180)
            global MyDate
    
            # создаем стиль окна без кнопок закрытия и тд
            styleWindow = (
                wx.MINIMIZE_BOX|
                #wx.MAXIMIZE_BOX|
                #wx.RESIZE_BORDER|
                wx.CAPTION|
                wx.SYSTEM_MENU|
                wx.CLOSE_BOX|
                wx.CLIP_CHILDREN
                )

            wx.Frame.__init__(
                self, None, -1, "FileReceiver",
                style = styleWindow)
             
            #------------------------------------------------------------------------------
            #задаем иконку
            frameIcon = wx.Icon(os.getcwd() + "\\images\\BtnSendFile.png")
            self.SetIcon(frameIcon)

            #Creating thread for saving logs
            thr = LogThread()
            thr.setDaemon(True)
            thr.start()
        
            self.panel = MainPanel(self)
            self.CreateMenu()
            #self.Center()
            self.Fit()
            #self.Layout()
            self.Show(True)

        except Exception as Err:
            wx.MessageBox("Возникла ошибка при создании главного окна, код ошибки = " + str(Err), " ", wx.OK)
            wx.Exit()

    #-----------------------------------------------------------
    def CreateMenu(self):
        menuBar = wx.MenuBar()

        #addingFileMenu
        MenuFile = wx.Menu()
        menuBar.Append(MenuFile, "Файл")
        SendFile = MenuFile.Append(-1, "Передать файл")
        self.Bind(wx.EVT_MENU, self.panel.SendBtnFunc, SendFile)

        OffServer = MenuFile.Append(-1,"Запрет приёма файлов")
        self.Bind(wx.EVT_MENU, self.panel.RecvBtnFunc, OffServer)

        MenuFile.AppendSeparator()

        MenuExit = MenuFile.Append(-1,"Выход")
        self.Bind(wx.EVT_MENU, self.panel.OnCloseWindow, MenuExit)

        #addingSetMenu
        MenuSet = wx.Menu()
        menuBar.Append(MenuSet, "Настройки")
        PortSet = MenuSet.Append(-1, "Сетевой порт...")
        self.Bind(wx.EVT_MENU, self.panel.PortSetBtn, PortSet)

        DirSet = MenuSet.Append(-1,"Директория для сохранения...")
        self.Bind(wx.EVT_MENU, self.panel.DirSetBtn, DirSet)

        #addingInfoMenu
        MenuInfo = wx.Menu()
        menuBar.Append(MenuInfo, "Справка")
        Lic = MenuInfo.Append(-1, "О лицензии")
        self.Bind(wx.EVT_MENU, self.panel.OpenLic, Lic)

        Info = MenuInfo.Append(-1, "О программе")
        self.Bind(wx.EVT_MENU, self.panel.OpenInfo, Info)

        self.SetMenuBar(menuBar)
        
#=======================================
#=======================================
#=======================================
#=======================================
# panel
class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent = parent)
        #Image on Background
        self.frame = parent
        self.SetBackgroundColour(wx.Colour("#bfdee8"))

        #Here's loading last config and announcing
        self.Preparing()

        #Here's creating panel
        self.CreatePanel()

    #-----------------------------------------------------------
    def CreatePanel(self):
        global MyDir
        self.CommonVbox = CommonVbox = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 6, vgap = 6)
        CommonVbox.AddGrowableRow(0, 1)
        for col in range (0, 2):
            CommonVbox.AddGrowableCol(col, 1)

        self.CreatePanelElms()

    def CreatePanelElms(self):
        #-------------------------------------------------------------
        #Images for btns
        Images = ["BtnSendFile.png", "BtnReceive.png", "BtnNotReceive.png", "BtnFade.png"]
        BMPs = []
        ButtonSize = (130, 130)
        for Image in Images:
            Im = wx.Image(MyDir + "\\images\\" + Image).ConvertToBitmap()
            BMPs.append(ScaleBitmap(Im, ButtonSize))

        #SendFileBtn
        self.SendBtn = SimpleClickThrob(
            self, [BMPs[0], BMPs[-1]], 2, 1, AnswerTime = 100)
        self.SendBtn.SetToolTip("Отправить файл")
        self.SendBtn.Bind(wx.EVT_LEFT_DOWN, self.SendBtnFunc)
        self.SendBtn.SetSize(ButtonSize)

        #SendFileBtn
        self.RecvBtn = ChangeClickThrob(
            self, [BMPs[1], BMPs[2], BMPs[-1]], 3, 1, AnswerTime = 50)
        self.RecvBtn.SetCurrent(0)
        self.RecvBtn.SetToolTip("Your Server Port = " + str(self.Settings[3]))
        self.RecvBtn.Bind(wx.EVT_LEFT_DOWN, self.RecvBtnFunc)
        self.RecvBtn.SetSize(ButtonSize)

        #for butt in [self.SendBtn, self.InfoBtn, self.LicBtn]:
        for butt in [self.SendBtn, self.RecvBtn]:
            self.CommonVbox.Add(butt, 0, wx.ALL|wx.ALIGN_CENTRE, 0)
          
        self.SetSizer(self.CommonVbox)
        self.Fit()

        # Добавляем слушателя
        pub.subscribe(self.UpdateDisplay, "UpdateMainWin")
        self.frame.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

#=====================================================================================
    #preparing different folders and peremennie
    def Preparing(self):
        
        # Creating folders
        global MyDir
        folders = ["Logs", "Received_Files"]

        for folder in folders:
            try:
                if folder not in os.listdir(MyDir):
                    os.mkdir(folder)
            except Exception as Err:
                ToLog("Can't create " + folder + " folder because of = " + str(Err))

        # Clear old logs
        ClearLogs()
        
        #self.Settings = [
        #               [MainPos],
        #               folder for received files,
        #               last client ip, last client port,
        #               ServerPort]
                     
        self.DefaultSettings = [
            [(100, 100)],
            MyDir + "\\Received_Files",
            ("192.168.1.1", 10002),
            10002]
        self.CurMd5 = None

        self.MakeDefaultSettings()
        #Loading last cfg
        self.keywords = ["MyPos", "PathToSave", "LastClient", "ServerPort"]
        
        self.LoadConfig()
        
        #Moving to last pos
        try:
            self.frame.Move((int(self.Settings[0][0]), int(self.Settings[0][1])))
        except Exception as Err:
            ToLog("Error moving Main Window, Error code = " + str(Err))

        #creating RecThread
        self.CreateThreads()
        
        return

#==================================================================================
    def LoadConfig(self):
        #try opening last profile
        global MyDir
        try:
            ToLog("LoadConfig function started")
            with open(MyDir + "\\lastcfg.cfg", "r") as file:
                Strings = file.read().splitlines()
                #print(str(Strings))
                file.close()

            #self.Settings = [
            #               [MainPos],
            #               folder for received files,
            #               last client ip, last client port,
            #               ServerPort]
            for String in Strings:
                if len(String) == 0:
                    continue
                String = String.split(maxsplit = 1)
                #print("string after Split = " + str(String))
                if String[0] == self.keywords[0]:
                    self.Settings[0] = (String[1].split()[0], String[1].split()[1])
                elif String[0] == self.keywords[1]:
                    self.Settings[1] = String[1]
                elif String[0] == self.keywords[2]:
                    self.Settings[2] = (String[1].split()[0], String[1].split()[1])
                elif String[0] == self.keywords[3]:
                    self.Settings[3] = String[1].split()[0]

            for Set in [self.Settings[0][0], self.Settings[0][1], self.Settings[2][1], self.Settings[3]]:
                if Set.isdigit():
                    Set = int(Set)
                else:
                    ToLog("Error loading setting = " + Set + "in lastconfig file")
                    self.MakeDefaultSettings()
                    return
                          
            #trying loaded path
            try:
                os.chdir(self.Settings[1])
            except Exception as Err:
                wx.MessageBox(
                    "При проверке пути для сохранения файлов аудиозаписи" +
                    "\nвозникла ошибка:" + "\n\n" + str(Err) +
                    "\n\nПуть для сохранения изменён на " +
                    MyDir + "\\Received_Files"," ", wx.OK)
                self.Settings[1] = MyDir + "\\Received_Files"

        except Exception as Err:
            ToLog("Failed to load config from file, Error code = " + str(Err))
            #raise Exception
            self.MakeDefaultSettings()

        else:
            ToLog("Succesfully loaded Settings:")
            for strings in self.Settings:
                ToLog("\t" + str(strings))
            

#===============================================================================
    def MakeDefaultSettings(self):
        ToLog("MakeDefaultSettings function started")
        self.Settings = self.DefaultSettings[:]
        ToLog("MakeDefaultSettings function finished")       

#===============================================================================
    #save config
    def SaveConfig(self):
        global MyDir
        try:
            ToLog("AutoSave function started")
            with open(MyDir + "\\lastcfg.cfg", "w") as file:
            
            #self.Settings = [
            #               [MainPos],
            #               folder for received files,
            #               last client ip, last client port,
            #               ServerPort]

                MyPos = self.frame.GetPosition()
                writing = [
                    "---------------------BeginOfFile---------------------",
                    self.keywords[0] + " " + str(MyPos[0]) + " " + str(MyPos[1]),
                    self.keywords[1] + " " + str(self.Settings[1]),
                    self.keywords[2] + " " + str(self.Settings[2][0]) + " " + str(self.Settings[2][1]),
                    self.keywords[3] + " " + str(self.Settings[3]),
                    "---------------------EndOfFile---------------------"]

                ToLog("Saved params:")
                for word in writing:
                    file.write(word + "\n")
                    ToLog("\t" + word)

                file.close()   

        except Exception as Err:
            ToLog("Error in AutoSavefunction, Error code = " + str(Err))
            #raise Exception
        else:
            ToLog("AutoaSave function finished succesfully")
        return
    
#=======================================================================================
    #Licence
    def OpenLic(self, evt):
        global MyDate
        try:
            ToLog("License button pressed")
            LICENSE = (
                "Данная программа является свободным программным обеспечением\n"+
                "Вы вправе распространять её и/или модифицировать в соответствии\n"+
                "с условиями версии 2 либо по Вашему выбору с условиями более\n"+
                "поздней версии Стандартной общественной лицензии GNU, \n"+
                "опубликованной Free Software Foundation.\n"+
                "Подробнее Вы можете ознакомиться с лицензией по ссылке " +
                "https://www.gnu.org/licenses/gpl-3.0.html\n\n\n" + 
                "Эта программа создана в надежде, что будет Вам полезной, однако\n"+
                "на неё нет НИКАКИХ гарантий, в том числе гарантии товарного\n"+
                "состояния при продаже и пригодности для использования в\n"+
                "конкретных целях.\n"+
                "Для получения более подробной информации ознакомьтесь со \n"+
                "Стандартной Общественной Лицензией GNU.\n\n"+
                "Данная программа написана на Python\n\n"
                "Автор: Титовский С.А.\n" +
                "Версия 0.3.0 от " + MyDate +
                "\n 0.2.0 Добавлена полоса прогресса передачи файлов" +
                "\n 0.3.0 Добавлена возможность отмены передачи и диалоги с пользователем")
            wx.MessageBox(LICENSE, "Лицензия", wx.OK)
        except Exception as Err:
            ToLog("Error in OpenLic func, Error code = " + str(Err))
            #raise Exception
        return

#==============================================================================================
    def OpenInfo(self, event):
        ToLog("OpenInfo button pressed")
        try:
            path = os.path.realpath(self.MyDir + "\\info")
            os.startfile(path + "\\AboutServer.pdf")
        except Exception as Err:
            try:
                os.startfile(path)
            except Exception as Err:
                wx.MessageBox("Возникла ошибка при открытии папки со справкой", "Справка", wx.OK)
                ToLog("Ошибка показа справки с кодом = " + str(Err))
        return

#=======================================================================================
    # Close Clicked
    def OnCloseWindow(self, evt):
        ToLog("Close Button Clicked")
        try:
            self.SaveConfig()
            print("waiting for end of thread")
            for thread in [self.TransvThread, self.ReceiverThread]:
                thread.OffThread()
            ToLog("Application closed")
            evt.Skip()
            wx.Exit()
            sys.exit()

        except Exception as Err:
            ToLog("Failed to closing program, Error code = " + str(Err))
            ToLog("Application closed")
            wx.Exit()
            sys.exit()
            #raise Exception
            
#=========================================
    def PortSetBtn(self, evt):
        try:
            ToLog("PortSetBtn Pressed")
            Dlg = EnterPortDlg(Port = str(self.Settings[3]))
            if Dlg.ShowModal() == wx.ID_OK:
                if Dlg.EnteredValue[0].GetValue().isdigit():
                    self.Settings[3] = int(Dlg.EnteredValue[0].GetValue())
                    if self.ReceiverThread != None:
                        self.RefreshThreadPams(self.ReceiverThread, self.Settings)
                    ToLog(
                        "New Server parameters was Entered:" +
                        "\n\t Port = " + str(self.Settings[3]))
                    self.RecvBtn.SetToolTip("Your Server Port = " + str(self.Settings[3]))
                else:
                    ToLog("Value of Port is not digit, Port of server didn't change")
                    wx.MessageBox("Введенное значение порта не является целым числом", " ", wx.OK)

        except Exception as Err:
            ToLog("Error in PortSetBtn, Error code = " + str(Err))
            #raise Exception

#=========================================
    def DirSetBtn(self, evt):
        try:
            ToLog("DirSetBtn pressed")
            dlg = wx.DirDialog (None, "Выберите директорию для сохранения принимаемых файлов", " ",
                                wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
            if dlg.ShowModal() != wx.ID_OK:
                return
            else:
                result = dlg.GetPath()
                self.Settings[1] = result
                ToLog("Changed directory for saving files, new dir = " + result)

                if self.ReceiverThread != None:
                    self.RefreshThreadPams(self.ReceiverThread, self.Settings)
        except Exception as Err:
            ToLog("Error in DirSetBtn, Error code = " + str(Err))
        else:
            ToLog("DirSetBtn finished successfully")
#=========================================
    def RecvBtnFunc(self, evt):
        try:
            ToLog("RecvBtn function started")
            if self.ServEvt.isSet():
                dlg = wx.MessageDialog(self, "Запретить прием файлов от других пользователей?", " ", wx.YES_NO)
                dlg.SetYesNoLabels("&Да", "&Нет")
                if dlg.ShowModal() != wx.ID_YES:
                    return
                else:
                    self.ServEvt.clear()
                    self.RecvBtn.Clicked(1)
                    self.RecvBtn.SetToolTip("Приём файлов запрещён пользователем")
                    ToLog("Receiving thread changed status to waiting")
                
            else:
                dlg = wx.MessageDialog(self, "Разрешить прием файлов от других пользователей?", " ", wx.YES_NO)
                dlg.SetYesNoLabels("&Да", "&Нет")
                if dlg.ShowModal() != wx.ID_YES:
                    return
                else:
                    self.ServEvt.set()
                    self.RecvBtn.Clicked(0)
                    self.RecvBtn.SetToolTip("Ваш сеетвой порт = " + str(self.Settings[3]))
                    ToLog("Receiving thread changed status to running")
                    self.ShowServerInfo()
                    
        except Exception as Err:
            ToLog("Error on RecvBtnFunc, Error code = " + str(Err))
            #raise Exception
        else:
            ToLog("RecvBtn function finished successfully")

#=========================================
    def ShowServerInfo(self):
        try:
            textDomain = "Ваше доменное имя = " + str(socket.gethostbyaddr("localhost")[0])
            ToLog("Obtained Domain Name = " + str(socket.gethostbyaddr("localhost")[0]))
        except Exception as Err:
            textDomain = "Возникла ошибка при определении имени домена, определите имя самостоятельно или обратитесь к администратору"
            ToLog("Error obtain Domain name, Error code = " + str(Err))
            #raise Exception

        try:
            tupIP = socket.gethostbyname_ex(socket.gethostname())[-1]
            if len(tupIP) == 1:
                textIP = "Ваш IP = " + str(socket.gethostbyaddr("localhost")[0])
            else:
                textIP = "Ваш ПК определил несколько IP: "
                for word in tupIP:
                    textIP = textIP + "\n" + word
            ToLog("Obtained IP-address = " + str(tupIP))
        except Exception as Err:
            textIP = "Возникла ошибка при определении IP адреса ПК, определите самостоятельно или обратитесь к администратору"
            ToLog("Error obtain IP address, Error code = " + str(Err))
            #raise Exception

        textPort = "Выш сетевой порт = " + str(self.Settings[3]) + "\nСообщите данные удалённому Клиенту"

        try:
            wx.MessageBox(textIP + "\n" + textDomain + "\n" + textPort, " ", wx.OK)
            if self.RecvBtn.GetCurrent() == 0:
                self.RecvBtn.SetToolTip(textIP + "\n" + textDomain + "\n" + textPort)
        except Exception as Err:
            ToLog("Error in Show Server Info, Error code = " + str(Err))
            #raise Exception
                                
#=========================================
    def CreateThreads(self, QueueThread = True):
        try:
            self.TransvThread = None
            self.ServEvt = threading.Event()
            self.ReceiverThread = ReceiverThread("ReceiverThread", self.ServEvt, self.Settings)
            threads = [self.ReceiverThread]
            
            for thread in threads:
                thread.setDaemon(True)
                thread.start()
                
        except Exception as Err:
            ToLog("Error in CreateThreads func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def TryThread(self, thread):
        try:
            if thread.is_alive() == False or thread == None:
                return "dead"
            else:
                return thread.TryThread()
        except Exception as Err:
            ToLog("Error in TryThread func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def RefreshThreadPams(self, thread, pams):
        try:
            thread.RefreshPams(pams)
        except Exception as Err:
            ToLog("Error in RefreshThreadPams func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def ResumeThread(self, thread):
        try:
            thread.Resume()
        except Exception as Err:
            ToLog("Error in ResumeThread func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def PauseThread(self, thread):
        try:
            thread.Pause()
        except Exception as Err:
            ToLog("Error in PauseThread func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def OffThread(self, thread):
        try:
            thread.OffThread()
        except Exception as Err:
            ToLog("Error in OffThread func, Error code = " + str(Err))
            #raise Exception
#==========================================
    def StartTransvThread(self):
        self.ClntEvt = threading.Event()
        self.TransvThread = TransiverThread("TransiverThread", self.ClntEvt, self.Settings)
        threads = [self.TransvThread]
            
        for thread in threads:
            thread.setDaemon(True)
            thread.start()

        ToLog("StartTransvThread function finished successfully")
#===================================
    #SendBtn pressed
    def SendBtnFunc(self, evt):
        ToLog("SendBtnFunc Started")
        try:
            self.CurMd5 = False
            if self.TransvThread == None:
                file = self.ChooseFile()
            elif self.TransvThread.is_alive() == False:
                file = self.ChooseFile()
            else:
                ToLog("Transv thread is already running")
                wx.MessageBox("Поток передачи файлов уже в работе", " ", wx.OK)
                return
            
            if file == False:
                return
            
        except Exception as Err:
            ToLog("Error in ChooseFile, Error code = " + str(Err))
            wx.MessageBox("Произошла ошибка при выборе файла, код ошибки = " + str(Err), " ", wx.OK)
            #raise Exception
            return
        
        try:
            self.EnterServerPams()
        except Exception as Err:
            ToLog("Error in EnterServerPams, Error code = " + str(Err))
            wx.MessageBox("Произошла ошибка при вводе параметров сервера, код ошибки = " + str(Err), " ", wx.OK)
            #raise Exception
            return

        if self.CheckMd5Thread.is_alive() == True:
            result = self.WaitMd5(file)
            ToLog("Result of WatMd5 = " + result)
            if result == "False":
                wx.MessageBox("Произошла ошибка при определении хэш md5 файла " + file, " ", wx.OK)
                return

        if self.CurMd5 == "False":
            ToLog("Error in finding Md5 hash of file " + file)
            wx.MessageBox("Произошла ошибка при определении хэш md5 файла " + file, " ", wx.OK)
            return
                
        try:
            self.StartTransvThread()
            self.TransvThread.RenewFile([file, self.CurMd5])
        except Exception as Err:
            ToLog("Error in RenewFile, Error code = " + str(Err))
            #raise Exception
        ToLog("SendBtnFunc Finished")

#====================================
    #ChooseFile
    def ChooseFile(self):
        DialogLoad = wx.FileDialog(
            self,
            "Выберите файл для отправки",
            #defaultDir = MyDir + "\\MyProfiles",
            #wildcard = "CFG files (*.cfg)|*cfg",
            style = wx.FD_OPEN)
        if DialogLoad.ShowModal() == wx.ID_CANCEL:
            return False
        else:
            Dir = DialogLoad.GetDirectory()
            file = DialogLoad.GetDirectory() + "\\" + DialogLoad.GetFilename()

            self.CheckMd5Thread = Md5Thread("Md5", self, file, self.Settings)
            self.CheckMd5Thread.setDaemon(True)
            self.CheckMd5Thread.start()
                        
            return file
#======================================
    #Wait for Md5 counting
    def WaitMd5(self, file):
        try:
            ToLog("Wait Md5 function started")
            WarnDlg = wx.GenericProgressDialog(
                "",
                "Подождите, пока происходит подсчёт хэш md5 файла " + file,
                maximum = 5,
                parent = self.frame,
                style = wx.PD_AUTO_HIDE|wx.PD_SMOOTH)
                #style = wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_SMOOTH)
            while True:
                if self.CheckMd5Thread.is_alive() == True:
                    #ToLog("Md5 not counted yet, wait 0.2 sec")
                    wx.MilliSleep(200)
                    continue
                ToLog("Md5Thread finished, waiting for summ")
                break

            while True:
                if isinstance (self.CurMd5, str):
                    break
                #ToLog("Wait 0.2 sec for new Md5 sending to MainWin")
                wx.MilliSleep(200)
                             
            WarnDlg.Destroy()
            ToLog("WaitMd5 function finished with CurMd5 = " + self.CurMd5)
            return self.CurMd5
        
        except Exception as Err:
            ToLog("Error in WaitMd5 function, Error code = " + str(Err))
            #raise Exception
            return "False"

#===================================
    #EnterServerPams
    def EnterServerPams(self):
        EnterDlg = EnterPamsDlg(IP = str(self.Settings[2][0]), Port = str(self.Settings[2][1]))
        if EnterDlg.ShowModal() == wx.ID_OK:
            if EnterDlg.EnteredValue[1].GetValue().isdigit():
                self.Settings[2] = (EnterDlg.EnteredValue[0].GetValue(), int(EnterDlg.EnteredValue[1].GetValue()))
            else:
                self.Settings[2] = (EnterDlg.EnteredValue[0].GetValue(), 10002)
                ToLog("Value of Port is not digit, Port Value set on 10002")
                wx.MessageBox("Введенное значение порта не является числом, значение порта сброшено до 10002", " ", wx.OK)

        ToLog(
            "New Remote Server parameters was Entered:" +
            "\n\t IP = " + self.Settings[2][0] +
            "\n\t Port = " + str(self.Settings[2][1]))

        if self.TransvThread != None:
            self.RefreshThreadPams(self.TransvThread, self.Settings)

#=============================================================================================
    #CreateProgrDlg
    def OpenUpdDlg(self, text, file, size):
        self.UpdDlg = wx.GenericProgressDialog(
            "",
            text + " (0 из" + str(size) + ") байт",
            maximum = size,
            parent = self.frame,
            #style = wx.PD_AUTO_HIDE|wx.PD_SMOOTH)
            style = wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_SMOOTH|wx.PD_CAN_ABORT)
        
#=============================================================================================
    # Updating Window
    def UpdateDisplay(self, mess):
        try:
            #ToLog("Message to MainWin = " + str(mess))
            if mess == "CloseDlg":
                try:
                    self.UpdDlg.Destroy()
                except Exception:
                    pass
            elif mess == "closeAsk":
                self.ansdlg.Destroy()
            elif mess == "AnsweredOK":
                self.OpenUpdDlg(
                    "Получение файла " + self.FileAskWin,
                    self.FileAskWin, self.SizeAskWin + 2000)
                self.ReceiverThread.SetAskMainWin("agreed")
            elif mess == "AnsweredCancel":
                self.ReceiverThread.SetAskMainWin("deslined")
                 
            if isinstance(mess, list):
                if mess[0] == "showWin":
                    wx.MessageBox(mess[1], " ", wx.OK)
                elif mess[0] == "AskWin":
                    self.ansdlg = AskFrame(parent = self.frame, text = mess[1])
                    self.FileAskWin = mess[2]
                    self.SizeAskWin = mess[3]
                  
                elif mess[0] == "RecUpdate":
                    if self.UpdDlg.WasCancelled() == True:
                        ToLog("UpdDlg was cancelled")
                        self.ReceiverThread.BreakConnection()
                        self.UpdDlg.Destroy()
                    else:
                        self.UpdDlg.Update(
                            mess[1],
                            "Получение файла " + mess[2] +
                            " (" +  str(mess[1]) + " из " + str(mess[3]) + ") байт")                          
                elif mess[0] == "newPort":
                    self.Settings[3] = mess[1]
                    self.ShowServerInfo()
                elif mess[0] == "fileSuccess":
                    self.UpdDlg.Destroy()
                    wx.MessageBox(
                        "Файл " + str(mess[1]) + " размером " + str(mess[2]) +
                        " получен успешно", " ", wx.OK)
                    global MyDir
                    os.startfile(self.Settings[1])
                elif mess[0] == "OpenTrDlg":
                    self.OpenUpdDlg(
                        "Передача файла " + mess[1],
                        mess[1], mess[2] + 2000)
                elif mess[0] == "TrUpdate":
                    if self.UpdDlg.WasCancelled() == True:
                        ToLog("UpdDlg was cancelled")
                        self.TransvThread.OffThread()
                        self.TransvThread.join()
                        self.UpdDlg.Destroy()
                    else:
                        self.UpdDlg.Update(
                            mess[1],
                            "Передача файла " + mess[2] +
                            " (" +  str(mess[1]) + " из " + str(mess[3]) + ") байт")
                elif mess[0] == "SendFileSuccess":
                    self.UpdDlg.Destroy()
                    wx.MessageBox(
                        "Файл " + str(mess[1]) + " размером " + str(mess[2]) + " был передан",
                        " ", wx.OK)
                elif mess[0] == "CheckRecMd5":
                    self.UpdDlg.Update(
                        self.UpdDlg.GetValue(),
                        "Подождите, пока происходит подсчёт хэш md5 файла " + mess[1])
                elif mess[0] == "NotOkMd5":
                    self.UpdDlg.Destroy()
                    wx.MessageBox(
                        "Полученный файл " + mess[1] + "может быть повреждён" +
                        "\n Хэш md5 файла (" + mess[3] +
                        ") не совпадает с контрольным значением (" + mess[2] + ")" +
                        "\nПопробуйте переслать файл повторно"," ", wx.OK)
                elif mess[0] == "OpenWaitWin":
                    self.WaitDlg = wx.GenericProgressDialog(
                        "",
                        "Ожидание ответа " + mess[2] + " на получение " + mess[1] + " (" + str(mess[3]) + ") сек",
                        maximum = 1,
                        parent = self.frame,
                        style = wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_SMOOTH|wx.PD_CAN_ABORT)
                elif mess[0] == "EditWaitWin":
                    if self.WaitDlg.Update(0, "Ожидание ответа " + mess[2] + " на получение " + mess[1] + " (" + str(mess[3]) + ") сек")[0] == False:
                         self.WaitDlg.Destroy()
                         ToLog("UpdDlg was cancelled")
                         self.TransvThread.OffThread()
                         self.TransvThread.join()
                elif mess[0] == "AnsweredWaitWin":
                    self.WaitDlg.Destroy()
                elif mess[0] == "NotAnsweredWaitWin":
                    self.WaitDlg.Destroy()
                    wx.MessageBox(
                        mess[2] + " не ответил на запрос о передаче " + mess[1], " ", wx.OK)
                    self.TransvThread.OffThread()
                    self.TransvThread.join()
            
        except Exception as Err:
            ToLog("Error in Update Display, Error code = " + str(Err))
            #raise Exception

#Treads
#======================
#======================
#======================
#======================
#MyThreadClass
class MyThread(threading.Thread):
    def __init__(self, myname, evt, pams):
        super().__init__()
        self.pams = pams
        self.name = myname
        self.stop = False
        self.pause = False
        self.evt = evt

    #---------------------------------------------------
    def ToWin(self, message):
        try:
            wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = message)
            if message[0] == "RecUpdate" or message[0] == "TrUpdate":
                return
            else:
                ToLog("Message to MainWin from Thread = " + str(message))
        except Exception:
            ToLog("Не смог отправить сообщение в главное меню")
            #raise Exception
    #------------------------------------------------------
    def OffThread(self):
        ToLog("I'm " + self.name + " and I have stop command")
        self.evt.set()
        self.stop = True

    #------------------------------------------------------
    def Pause(self):
        ToLog("I'm " + self.name + " and I have pause command")
        #self.pause = True
        self.evt.clear()

    #-------------------------------------------------------
    def Resume(self):
        ToLog("I'm " + self.name + " and I have resume command")
        #self.pause = False
        self.evt.set()

    #-------------------------------------------------------
    def RefreshPams(self, pams):
        ToLog("I'm " + self.name + " and I have refresh pams command")
        self.pams = pams

    #-------------------------------------------------------
    def TryThread(self):
        if self.stop == True:
            return "dead"
        elif self.evt.isSet():
            return "running"
        else:
            return "waiting"

#======================
#======================
#======================
#======================
#NetConnectThread
class ReceiverThread(MyThread):
    #self.Settings = [
        #               [MainPos],
        #               folder for received files,
        #               last client ip, last client port,
        #               ServerPort]
    def __init__(self, name, evt, settings, timeout = 3):
        super().__init__(name, evt, settings)
        self.settings = settings
        self.socktimeout = timeout
        self.port = 10000
        self.evt.set()
        self.AnsMainWin = "None"
        self.RenewTime = 0.5
        self.breakConn = False
        
    #------------------------------------
    def run(self):
        while True:
            if self.stop == True:
                break
            #print("===============iter StartServer Thread==================")
            try:
                self.StartServer()
            except Exception as Err:
                ToLog("Error in self.StartServer, Error code = " + str(Err))
                raise Exception
                break
            self.evt.wait()
        ToLog("Receiver Thread finished")

    #---------------------------------------
    def FindFreePort(self, port = 10002, end = 16000):
        while True:
            if port > end:
                ToLog("Didn't find free port between " + str(port)  + " and " + str(end))
                self.ToWin(["showWin", "Не удалось найти свободный сетевой порт между " + str(port)  + " и " + str(end)])
                return False
            
            try:
                self.sock = socket.socket()
                self.sock.bind(("", port))
                if self.port != port:
                    self.ToWin(["newPort", port])
                    ToLog("Find free port = " + str(port))
                self.port = port
                self.sock.close()
                return True
            
            except socket.error as Err:
                ToLog("Port = " + str(port) + " is busy, trying next port")
                port = port + 1
                
    #---------------------------------------
    def StartServer(self):
        #ToLog("Server function started")
        #create socket with lifetime 1 sec
        if self.FindFreePort(port = int(self.settings[3])) == False:
            self.stop = True
            return

        self.sock = socket.socket()
        self.sock.bind(("", self.port))
        self.sock.settimeout(self.socktimeout)
        self.sock.listen(5)
        #ToLog("Prepared socked with port = " + str(self.port) + ", timeout = " + str(self.socktimeout))

        try:
            self.conn, self.addr = self.sock.accept()
            ToLog("Create TCP socket with client = " + str(self.addr))
            
            try:
                self.ReceiveFile()
            except Exception as Err:
                ToLog("Error in ReceiveFile, Error code = " + str(Err))
                #raise Exception
            
        except socket.timeout:
            #print("Socket lifetime exceed")
            pass
        except socket.error as msg:
            ToLog("SOCKET ERROR CODE = " + str(msg))
            ToLog("strerror" + os.strerror(msg.errno))
           
        except Exception as Err:
            ToLog("Error creating socket, Error code = " + str(Err))
            #raise Exception

        self.sock.close()
        #ToLog("Server function finished")

    #---------------------------------------
    def ReceiveFile(self, buff_size = 4096, sep = "<SEP>"):
        ToLog("ReceivedFile func started")
        
        global MyDir
        received = self.conn.recv(buff_size)
        received = pickle.loads(received)
        filename, size, md5 = received.split(sep)
        filename = os.path.basename(filename)
        size = int(size)
        self.RecBytes = 0

        self.AskForReceive(filename, size)

        if self.AnsMainWin == "agreed":

            self.startTime = time.time()
            filename = self.NameFile(filename, self.settings[1])
            self.breakConn = False
                    
            with open(self.settings[1] + "\\" + filename, "wb") as file:
                ToLog("Writing to file = "  + filename + "to dir = " + self.settings[1])
                while True:
                    if self.breakConn == True:
                        ToLog("Connection was broken after cancelling UpdDlg")
                        self.AnsMainWin = "None"
                        self.conn.sendall(b"break")
                        
                        return
                        
                    bytesRead = self.conn.recv(buff_size)
                    self.RecBytes = self.RecBytes + buff_size
                    if time.time() - self.startTime > self.RenewTime:
                        self.ToWin(["RecUpdate", self.RecBytes, filename, size])
                        self.startTime = time.time()
                    
                    if not bytesRead:
                        break
                    file.write(bytesRead)
                    self.conn.sendall(b"con")
                    
                file.close()

            resultMd5 = self.checkMd5(filename, size, md5)
            
        else:
            ToLog("Receiving deslined by user")

        ToLog("ReceivedFile func finished")
        self.AnsMainWin = "None"

    #---------------------------------------
    def checkMd5(self, file, size, md5Rec):
        try:
            self.ToWin(["CheckRecMd5", file])
            result = getMd5(self.settings[1] + "\\" + file)
            if result == md5Rec:
                ToLog("Received Md5 hash compare with hash of received file, " + file + " is OK")
                self.ToWin(["fileSuccess", file, size])
            else:
                ToLog(
                    "Received file " + file + "md5 hash ("  + result +
                    ") does not compare with control md5 hash (" + md5Rec + ")" +
                    "\nReceived file may be not OK, try to transcieve file again")
                self.ToWin(["NotOkMd5", file, md5Rec, result])
        except Exception as Err:
            ToLog("Error in checkMd5, Error code = " + str(Err))
            self.ToWin(["ErrMd5", file])


    #---------------------------------------
    def NameFile(self, Name, Dir):
        #ToLog("Name = " + Name)
        #ToLog("Dir = " + Dir)
        try:
            currFiles = ListFiles(Dir)
            if currFiles != False:
                if "." in Name:
                    ext = "." + Name[Name.rfind(".") + 1:]
                    FirstName = Name[:Name.rfind(".")]
                    ToLog("main, ext = " + FirstName  + ", " + ext)
                else:
                    ext = ""
                    FirstName = Name
                    ToLog("main, ext = " + FirstName  + ", " + ext)
                i = 1
                while True:
                    if Name not in currFiles:
                        ToLog("finally name of receiving file = " + Name)
                        return Name
                    Name = FirstName + "(" + str(i) + ")" + ext
                    i = i + 1
                    

        except Exception as Err:
            ToLog("Error in NameFile function, Error code = " + str(Err))
            return Name + "(errored)"

    #-------------------------------------------
    def AskForReceive(self, file, size):
        try:
            ToLog("AskForReceive function started")
            try:
                DomName = str(socket.gethostbyaddr(self.addr[0])[0])
                textDomain = ", domain name " + DomName
            except Exception as Err:
                ToLog("Error in obtain DomName of ip " + self.addr[0] + ", Error code = " + str(Err))
                textDomain = " "
            self.ToWin(["AskWin", "Пользователь " + self.addr[0] + textDomain + 
                        " пытается передать файл на Ваш ПК. \nПродолжить?" +
                        "\n\n\tИмя файла " + file + ", \n\tРазмер " +
                        str(size) + " (в байтах)", file, size])
            while True:
                #ToLog("self.AnsMainWin = " + self.AnsMainWin)
                if self.AnsMainWin != "None":
                    ToLog("Got answer from user for receiving, answer = " + self.AnsMainWin)
                    self.conn.sendall(pickle.dumps(self.AnsMainWin))
                    time.sleep(0.1)
                    self.conn.sendall(pickle.dumps(self.AnsMainWin))
                    ToLog("AskForReceive function finished")
                    return
                time.sleep(0.1)
                self.conn.sendall(pickle.dumps("wait"))
                if self.conn.recv(4096) == b"stop":
                    ToLog("Cancelled by transv side")
                    self.AnsMainWin = "deslined"
                    self.ToWin("closeAsk")

        except Exception as Err:
            ToLog("Error in AskForReceive function, Error code = " + str(Err))
            #raise Exception

    #------------------------------------------------
    def SetAskMainWin(self, answer):
        ToLog("Now AskMainWin = " + answer)
        self.AnsMainWin = answer

    #------------------------------------------------
    def BreakConnection(self):
        ToLog("Break connection function started")
        self.breakConn = True

#======================
#======================
#======================
#======================
#NetConnectThread
class TransiverThread(MyThread):
    #self.Settings = [
        #               [MainPos],
        #               folder for received files,
        #               last client ip, last client port,
        #               ServerPort]
    def __init__(self, name, evt, settings, timeout = 60):
        super().__init__(name, evt, settings)
        self.settings = settings
        self.socktimeout = timeout
        self.evt.clear()
        self.timeRefresh = 0.5

    #---------------------------------------
    def RenewFile(self, file):
        try:
            ToLog("RenewFile function started")
            self.filepath = file[0]
            self.md5 = file[1]
            self.evt.set()
            ToLog("RenewFile function finished, filepath = " + file[0] + ", md5 hash = " + file[1])
        except Exception as Err:
            self.evt.set()
            self.stop = True
            ToLog("Error in RenewFile function, Error code = " + str(Err))
            #raise Exception
        
    #------------------------------------
    def run(self):
        self.evt.wait()
        if self.stop == True:
            ToLog("End of ThransvThread")
            return

        try:
            self.StartConn()
        except socket.timeout:
            ToLog("End of connection, socket timeout exceed")
        except Exception as Err:
            ToLog("Error in StartConn, Error code = " + str(Err))
            self.ToWin(["showWin", str(Err)])

        ToLog("End of ThransvThread")
        self.ToWin("CloseDlg")
            
    #---------------------------------------
    def StartConn(self):
        ToLog("StartConn function started")
        self.sock = socket.socket()
        self.sock.settimeout(self.socktimeout + 10)
        sockAddr = self.settings[2]
        self.sock.connect(sockAddr)
        ToLog(
            "Connected TCP socket with server:" +
            "\n\tIP = " + str(self.settings[2][0]) +
            "\n\tPort = " + str(self.settings[2][1]))
        ToLog("StartConn function finished")
        
        try:
            self.TransvFile()
        except Exception as Err:
            ToLog("Error in TransvInfo, Error code = " + str(Err))
            try:
                self.sock.close()
            except Exception as Err:
                ToLog("Error in closing socket, Error code = " + str(Err))

    #---------------------------------------
    def TransvFile(self, buff_size = 4096, sep = "<SEP>"):
        ToLog("Start of TransvFile func" + self.filepath)
        with open(self.filepath, "rb") as File:
            #sending name and size of file
            FileSize = os.path.getsize(self.filepath)
            FileName = self.filepath.split("\\")[-1]
            
            a = pickle.dumps(f"{FileName}{sep}{FileSize}{sep}{self.md5}")
            self.sock.sendall(a)

            #wait for answer
            WaitThread = WaitingThread(FileName, self.settings[2][0], self.socktimeout)
            WaitThread.setDaemon(True)
            WaitThread.start()
            
            while True:
                recv = self.sock.recv(buff_size)
                recv = pickle.loads(recv)
                print("recv = " + recv)
                
                if not recv:
                    continue
                if recv == "wait":
                    if self.stop == True:
                        self.sock.send(b"stop")
                    else:
                        self.sock.send(b"ok")
                    continue
                elif recv == "agreed":
                    ToLog("Server agreed for receiving file")
                    WaitThread.GotAnswer()
                    break
                elif recv == "deslined":
                    ToLog("Server deslined for receiving file")
                    WaitThread.GotAnswer()
                    self.ToWin(["showWin", "Передача файла была отменена удалённой стороной"])
                    
                    self.sock.close()
                    return

            #sending bytes of file
            self.startTime = time.time()
            self.TrBytes = 0
            self.ToWin(["OpenTrDlg", FileName, FileSize])

            while True:
                if self.stop == True:
                    self.ToLog("Transv file was cancelled by user")
                    break
                bytes_read = File.read(buff_size)
                #time.sleep(0.1)
                #ToLog("sleep for 0.1")
                if not bytes_read:
                    break
                self.sock.sendall(bytes_read)
                self.TrBytes = self.TrBytes + buff_size
                if time.time() - self.startTime > self.timeRefresh:
                    self.ToWin(["TrUpdate", self.TrBytes, FileName, FileSize])
                    self.startTime = time.time()
                recv = self.sock.recv(buff_size)
                if recv == b"break":
                    ToLog("Transv file was cancelled by receiving side")
                    self.ToWin(["showWin", "Передача файла была отменена"])
                    break
                
        self.sock.close()
        ToLog("Finish of TransvFile " + self.filepath + ", size = " + str(FileSize))
        self.ToWin(["SendFileSuccess", FileName, FileSize])

#=============================================
#=============================================
#=============================================
#=============================================
# Thread for counting Md5
class Md5Thread(threading.Thread):
    def __init__(self, name, parent, file, settings):
        super().__init__()
        self.name = name
        self.parent = parent
        self.file = file
        self.settings = settings

    def run(self):
        ToLog("Md5Thread started!!!")
        self.CountMd5()
        ToLog("Md5Thread finished!!!")

    def CountMd5(self):
        try:
            ToLog("CountMd5 started")
            resultMd5 = getMd5(self.file)
            self.SendMd5(resultMd5)
            ToLog("CountMd5 finished")
        except Exception as Err:
            ToLog("Error in CountMd5 in Md5Thread, Error code = " + str(Err))
            self.SendMd5("False")

    def SendMd5(self, md5):
        try:
            ToLog("SendMd5 function started")
            self.parent.CurMd5 = md5
            ToLog("Now CurMd5 of MainWin = " + md5)
        except Exception as Err:
            ToLog("Error in SendMd5, Error code = " + str(Err))

#=============================================
#=============================================
#=============================================
#=============================================
# Thread for waiting window
class WaitingThread(threading.Thread):
    def __init__(self, file, addr, timeout):
        super().__init__()
        self.file = file
        self.addr = addr
        self.timeout = timeout
        self.stop = False
        self.answered = False

    def run(self):
        ToLog("WaitingThread started")
        self.CountingWin()
        ToLog("WaitingThread finished")

    def GotAnswer(self):
        try:
            ToLog("GotAnswer function started")
            self.answered = True
        except Exception as Err:
            ToLog("Error in GotAnswer, Error code = " + str(Err))

    def CountingWin(self):
        ToLog("CountingWin started")
        try:
            wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = ["OpenWaitWin", self.file, self.addr, self.timeout])
            for sec in range (0, self.timeout):
                if self.answered == True:
                    wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = ["AnsweredWaitWin", self.file, self.addr])
                    return
                    
                time.sleep(1)
                wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = ["EditWaitWin", self.file, self.addr, self.timeout - sec])
                sec = sec + 1

            wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = ["NotAnsweredWaitWin", self.file, self.addr])
        except Exception as Err:
            ToLog("Error in CountingWin, Error code = " + str(Err))
            wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = ["Answered", self.file, self.addr])
                   
#=============================================
#=============================================
#=============================================
#=============================================
#Return md5 of file in path
def getMd5(path):
    try:
        m = hashlib.md5()
        with open(path, "rb") as f:
            lines = f.read()
            m.update(lines)

        md5code = m.hexdigest()
        ToLog("Succesfully getMd5 from " + path + ", result = " + md5code)
        return md5code
    
    except Exception as Err:
        ToLog("Error in getMd5, Error code = " + str(Err))
        return "False"
        
    
#=============================================
#=============================================
#=============================================
#=============================================
#ListOfFiles
def ListFiles(Dir):
    try:
        listCommon = os.listdir(Dir)
        fullpaths = map(lambda name: os.path.join(Dir, name), listCommon)
        fileList = []
        dirList = []

        for file in fullpaths:
            #if os.path.isdir(file):
            #    dirList.append(file)
            if os.path.isfile(file):
                fileList.append(os.path.basename(file))

        ToLog("fileList in " + str(Dir) + " = " + str(fileList))
        return fileList
    
    except Exception as Err:
        ToLog("Error in ListFiles function, Error code = " + str(Err))
        return False

#=============================================
#=============================================
#=============================================
#=============================================
#Dialog of port Server
class EnterPortDlg(wx.Dialog):
    def __init__(
        self, label = "Введите порт локального сервера", Port = "9999"):
        self.label = label
        self.port = Port
        
        self.value = [self.port]
        
        wx.Dialog.__init__(self, None, -1, label)
        labels = ["Сетевой порт"]
        posSText = [(10, 10)]
        for i in range (0, len(labels)):
            text = wx.StaticText(self, wx.ID_ANY, labels[i], pos = posSText[i])
            text.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
        posText = [(10, 35)]
        self.EnteredValue = []
        for i in range(0, len(posText)):
            temp = wx.TextCtrl(self, wx.ID_ANY, "", pos = posText[i], size = (260, 30), style = wx.TE_CENTRE)
            temp.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
            temp.SetValue(self.value[i])
            self.EnteredValue.append(temp)

        OKButton = wx.Button(self, wx.ID_OK, "OK", pos = (75, 80), size = (120, 30))
        OKButton.SetDefault()
        OKButton.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
        self.SetClientSize((280, 120))
        self.Bind(wx.EVT_CLOSE, self.NoClose)

    def NoClose(self, evt):
        print("No Close")
    
#=============================================
#=============================================
#=============================================
#=============================================
#Dialog of authorizaion
class EnterPamsDlg(wx.Dialog):
    def __init__(
        self, label = "Введите данные удаленного абонента", IP = "192.168.1.1",
        Port = "9999"):
        self.label = label
        self.ip = IP
        self.port = Port
        
        self.value = [self.ip, self.port]
        
        #wx.Dialog.__init__(self, None, -1, label, size = (300,300))
        wx.Dialog.__init__(self, None, -1, label)
        labels = ["IP-адрес или доменное имя", "Сетевой порт"]
        posSText = [(10, 10), (10, 70)]
        for i in range (0, len(labels)):
            text = wx.StaticText(self, wx.ID_ANY, labels[i], pos = posSText[i])
            text.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
        posText = [(10, 35), (10, 95)]
        self.EnteredValue = []
        for i in range(0, len(posText)):
            temp = wx.TextCtrl(self, wx.ID_ANY, "", pos = posText[i], size = (260, 30), style = wx.TE_CENTRE)
            temp.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
            temp.SetValue(self.value[i])
            self.EnteredValue.append(temp)

        OKButton = wx.Button(self, wx.ID_OK, "OK", pos = (75, 140), size = (120, 30))
        OKButton.SetDefault()
        OKButton.SetFont(wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL))
        self.SetClientSize((280, 180))
        self.Bind(wx.EVT_CLOSE, self.NoClose)

    def NoClose(self, evt):
        print("No Close")
        
#=============================================
#=============================================
#=============================================
#=============================================
# scaling bitmaps
def ScaleBitmap(bitmap, size):
    image = bitmap.ConvertToImage()
    image = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
    return wx.Image(image).ConvertToBitmap()

#=================================
#=================================
#=================================
#=================================
# Окно приветствия
class MySplashScreen(SplashScreen):
    def __init__(self, MyDir, parent = None):
        super(MySplashScreen, self).__init__(
            bitmap = wx.Bitmap(name = MyDir + "\\BtnSendFile.png", type = wx.BITMAP_TYPE_PNG),
            splashStyle = wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_TIMEOUT,
            milliseconds = 1500,
            parent = None,
            id = -1,
            pos = wx.DefaultPosition,
            size = wx.DefaultSize,
            style =wx.STAY_ON_TOP | wx.BORDER_NONE)
        self.Show(True)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        event.Skip()
        self.Hide()

#=============================================
#=============================================
#=============================================
#=============================================
# SimpleClickThrob#1
class SimpleClickThrob(wx.lib.throbber.Throbber):
    def __init__(self, parent, ListOfFrames, NumOfFrames, FrameDelay, AnswerTime = 200, AnswerFrame = False):
        wx.lib.throbber.Throbber.__init__(self, parent, wx.ID_ANY, ListOfFrames, frames = NumOfFrames, frameDelay = FrameDelay)
        print("New SimpleThrob object created")
        self.CurFrame = 0
        self.AnswerTime = AnswerTime
        if AnswerFrame == False:
            self.AnswerFrame = NumOfFrames - 1
        else:
            self.AnswerFrame = AnswerFrame
        #print("AnswerFrame = " + str(self.AnswerFrame))

    def Clicked(self):
        #print("Clicked func started")
        self.SetCurrent(self.AnswerFrame, clicked = True)
        wx.MilliSleep(self.AnswerTime)
        self.SetCurrent(self.CurFrame, clicked = True)
        #print("Clicked func ended")
        
    def SetCurrent(self, num, clicked = False):
        wx.lib.throbber.Throbber.SetCurrent(self, num)
        if clicked == False:
            self.CurFrame = num
            #print("Now CurFrame = " + str(self.CurFrame))

    def GetCurrent(self):
        #print("asked CurFrame")
        return self.CurFrame
#=============================================
#=============================================
#=============================================
#=============================================
# mythrob#2
class ChangeClickThrob(wx.lib.throbber.Throbber):
    def __init__(self, parent, ListOfFrames, NumOfFrames, FrameDelay, AnswerTime = 200, AnswerFrame = False):
        wx.lib.throbber.Throbber.__init__(self, parent, wx.ID_ANY, ListOfFrames, frames = NumOfFrames, frameDelay = FrameDelay)
        print("I created my throbber class")
        self.CurFrame = 0
        self.AnswerTime = AnswerTime
        if AnswerFrame == False:
            self.AnswerFrame = NumOfFrames - 1
        else:
            self.AnswerFrame = AnswerFrame
        #print("AnswerFrame = " + str(self.AnswerFrame))

    def Clicked(self, EndFrame):
        #print("Clicked func started")
        self.SetCurrent(self.AnswerFrame, clicked = True)
        wx.MilliSleep(self.AnswerTime)
        self.SetCurrent(EndFrame)
        #print("Clicked func ended")
        
    def SetCurrent(self, num, clicked = False):
        wx.lib.throbber.Throbber.SetCurrent(self, num)
        if clicked == False:
            self.CurFrame = num
            #print("Now CurFrame = " + str(self.CurFrame))

    def GetCurrent(self):
        #print("asked CurFrame")
        return self.CurFrame

#=============================================
#=============================================
#=============================================
#=============================================
class AskFrame(wx.Frame):
    def __init__(
        self, parent = None, label = " ", text = "Enter text",
        btnOk = "Да", btnCancel = "Нет"):
        
  
        #wx.Frame.__init__(self, None, -1, label)
        wx.Frame.__init__(
            self, parent, -1, "label",
            #style = wx.FRAME_SHAPED)
            style = wx.FRAME_SHAPED|wx.RESIZE_BORDER|wx.STAY_ON_TOP)

        #self.sizer = sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = sizer = wx.FlexGridSizer(rows = 2, cols = 1, hgap = 6, vgap = 6)
        sizer.AddGrowableRow(0, 0)
        sizer.AddGrowableCol(0, 1)

        
        flexsizer = wx.FlexGridSizer(rows = 1, cols = 2, hgap = 6, vgap = 6)
        flexsizer.AddGrowableCol(0, 1)
        flexsizer.AddGrowableCol(1, 1)

        self.firsttext = text
        self.text = wx.StaticText(self, wx.ID_ANY, text)
        self.text.Bind(wx.EVT_SIZE, self.WrapText)
        self.text.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.text.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.text.Bind(wx.EVT_MOTION, self.OnMouseMove)
        sizer.Add(self.text, -1, wx.ALL | wx.EXPAND , border = 5)
        
        self.OkBtn = OKButton = wx.Button(self, wx.ID_OK, btnOk)
        OKButton.Bind(wx.EVT_BUTTON, self.OKPushed)
        OKButton.SetDefault()
        flexsizer.Add(OKButton, -1, wx.ALIGN_CENTRE, 5)

        CancelButton = wx.Button(self, wx.ID_OK, btnCancel)
        CancelButton.Bind(wx.EVT_BUTTON, self.CancelPushed)
        flexsizer.Add(CancelButton, -1, wx.ALIGN_CENTRE, 0)
        sizer.Add(flexsizer, 0, wx.EXPAND|wx.ALL, 0)

        #preparing
        self.delta = wx.Point(0, 0)
        self.Center()
        self.pos = self.GetPosition()

        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU)
        self.SetBackgroundColour(colour)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)

        self.SetSizer(sizer)
        
        self.SetMaxSize((1000, 1000))
        self.Layout()
        self.Fit()

        self.ResizeFrame()


        self.Move(self.pos)
        self.Show(True)
        
    def WrapText(self, evt):  
        self.text.SetLabel(self.firsttext)
        self.text.Wrap(self.GetClientSize()[0])
        textsize = self.text.GetSize()

    def ResizeFrame(self):
        while True:
            textsize = self.text.GetSize()
            print("txtsize = " + str(textsize))
            print("clnt size = " + str(self.GetClientSize()))
            if self.GetClientSize()[1] > 990:
                break
            if (textsize[1]  + 40) > self.GetClientSize()[1]:
                break
            self.SetClientSize((self.GetClientSize()[0], self.GetClientSize()[1] + 5))
            print("set clnt size " + str(self.GetClientSize()[1] + 5))
                  
    def OKPushed(self, evt):
        ToLog("OKPushed")
        wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = "AnsweredOK")
        self.Destroy()
        
    def CancelPushed(self, evt):
        wx.CallAfter(pub.sendMessage, "UpdateMainWin", mess = "AnsweredCancel")
        self.Destroy()
    
    #==================================================================
    def OnLeftDown(self, evt):
        self.CaptureMouse()
        clickedPos = self.ClientToScreen(evt.GetPosition())
        origin = self.GetPosition()
        self.delta = wx.Point(clickedPos.x - origin.x, clickedPos.y - origin.y)
        
#========================================================================
    def OnMouseMove(self, evt):
        if evt.Dragging() and evt.LeftIsDown():
            pos = self.ClientToScreen(evt.GetPosition())
            newPos = (pos.x - self.delta.x, pos.y - self.delta.y)
            self.pos = newPos
            self.Move(newPos)
            
#======================================================================
    def OnLeftUp(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()
        
#=============================================
#=============================================
#=============================================
#=============================================
# ClearOldLogs
def ClearLogs():
    global LogDir
    try:
        while len(os.listdir(LogDir)) >= 10:
            if len(os.listdir(LogDir)) < 10:
                    break
            try:
                os.remove(os.path.abspath(FindOldest(LogDir)))
                print("DELETING FILE " + str(FindOldest(LogDir)))
            except Exception as Err:
                ToLog("Old file with logs wasn't deleted, Error code = " + str(Err))
                #raise Exception
                break
    except Exception as Err:
        ToLog("Error of clearing dir with logs, Error code = " + str(Err))
        #raise Exception
#=============================================
#=============================================
#=============================================
#=============================================   
# DeleteOldest
def FindOldest(Dir):
    try:
        List = os.listdir(Dir)
        fullPath = [Dir + "/{0}".format(x) for x in List]
        oldestFile = min(fullPath, key = os.path.getctime)
        return oldestFile
    except Exception as Err:
        ToLog("Error of finding oldest file in dir, Error code = " + str(Err))
        #raise Exception
        return False

#=============================================
#=============================================
#=============================================
#=============================================
# Tolog - renew log
def ToLog(message, startThread = False):
    try:
        global LogQueue
        LogQueue.put(str(datetime.today())[10:19] + "  " + str(message) + "\n")
    except Exception as Err:
        print("Error in ToLog function, Error code = " + str(Err))
        
#=============================================
#=============================================
#=============================================
#=============================================
# Thread for saving logs
class LogThread(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        global LogQueue
        ToLog("LogThread started!!!")
        self.writingQueue()
        ToLog("LogThread finished!!!")

    def writingQueue(self):
        global LogQueue
        while True:
            try:
                if LogQueue.empty():
                    time.sleep(3)
                    continue
                else:
                    with open(LogDir + "\\" + str(datetime.today())[0:10] + ".cfg", "a") as file:
                        while not LogQueue.empty():
                            mess = LogQueue.get_nowait()
                            file.write(mess)
                            print("Wrote to Log:\t" + mess)
                        file.close()
            except Exception as Err:
                print("Error writing to Logfile, Error code = " + str(Err))
                #raise Exception

'''============================================================================'''
# Определение локали!
locale.setlocale(locale.LC_ALL, "")

global LogDir, MyDir, MyDate, LogQueue
LogDir = os.getcwd() + "\\Logs"
LogQueue = queue.Queue()
MyDate = " 16.01.2024"
MyDir = os.getcwd()

ToLog("Application started")

ex = wx.App()

WINDOW = MySplashScreen(MyDir + "\\images")
MainWindow()


ex.MainLoop()





     
