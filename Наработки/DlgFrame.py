import wx
import string
import socket
import os
import time

class dlg(wx.Frame):
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
        print("OKPushed")
        self.Destroy()
    def CancelPushed(self, evt):
        print("CancelPushed")
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
        
    #=====================================================================================
        
app = wx.App()
text = ('''Вы уверены, что хотите принять файл "Абракадарбра"?''' + "\n") * 5
dlg1 = dlg(text = text)
app.MainLoop()
