'Formats the saved Hours Breakdown file for client IA1;
' - Adds Subtotals to the dataset
' - Formats the Font and Background properties


On Error Resume Next


Dim objExcel, Wkbk, Wksht

Set objExcel = CreateObject("Excel.Application")
Set Wkbk = objExcel.Workbooks.Open(WScript.Arguments.Item(0))
If Err.Number = 0 Then
	Set Wksht = Wkbk.Sheets(1)
	
	AddSubtotals
	
	FormatHeader
	
	WScript.StdOut.Writeline "SUCCESS"
Else
	WScript.StdOut.Writeline "An error occurred when accessing the Hours Breakdown file." +_
	vbNewLine + vbNewLine + "Error Desc.: " + Err.Description
	Err.Clear
End If

Wkbk.Save()
WScript.Sleep 2000
Wkbk.Close
WScript.Sleep 2000
objExcel.Quit
Set Wkbk = Nothing
Set Wksht = Nothing


Function AddSubtotals()
'Adds Subtotals to the dataset

	Wksht.UsedRange.Subtotal 1, -4157, Array(3), True
	Wksht.Outline.ShowLevels 2
End Function


Function FormatHeader()
'Formats the Font and Background properties of the header row

	Wksht.Range("A1:C1").Font.Bold = True
	With Wksht.Range("A1:C1").Interior
        .ThemeColor = 1
        .TintAndShade = -0.249977111117893
        .PatternTintAndShade = 0
	End With
	
	Wksht.Range("A1:C1").EntireColumn.AutoFit
End Function
