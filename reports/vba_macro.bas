Attribute VB_Name = "ReconciliationAutomation"

Option Explicit

Sub RunQuickReconciliationAudit()
    Dim startTime As Double
    startTime = Timer

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    Call ApplyExceptionColorHighlighting
    Call AutoFitAllSheets
    Call CreateDynamicFilters

    Application.ScreenUpdating = True
    Application.DisplayAlerts = True

    Dim elapsedTime As Double
    elapsedTime = Round(Timer - startTime, 2)
    
    MsgBox "Reconciliation Audit completed in " & elapsedTime & " seconds!" & vbCrLf & _
           "All exceptions styled, critical variances flagged (> $1,000), and auto-filters active.", _
           vbInformation, "Reconciliation Automation Suite"
End Sub

Sub ApplyExceptionColorHighlighting()
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Exceptions Breakdown")
    On Error GoTo 0
    
    If ws Is Nothing Then Exit Sub

    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then Exit Sub

    Dim r As Long
    Dim category As String
    Dim amtDiff As Double

    For r = 2 To lastRow
        category = Trim(UCase(ws.Cells(r, 2).Value))
        amtDiff = Abs(Val(ws.Cells(r, 7).Value))

        Select Case category
            Case "AMOUNT_MISMATCH"
                ws.Cells(r, 2).Interior.Color = RGB(255, 235, 156)
                ws.Cells(r, 2).Font.Color = RGB(156, 101, 0)
            Case "MISSING_IN_LEDGER"
                ws.Cells(r, 2).Interior.Color = RGB(255, 199, 206)
                ws.Cells(r, 2).Font.Color = RGB(156, 0, 6)
            Case "MISSING_IN_BANK"
                ws.Cells(r, 2).Interior.Color = RGB(252, 228, 214)
                ws.Cells(r, 2).Font.Color = RGB(198, 89, 17)
            Case "DUPLICATE_IN_BANK", "DUPLICATE_IN_LEDGER"
                ws.Cells(r, 2).Interior.Color = RGB(235, 220, 245)
                ws.Cells(r, 2).Font.Color = RGB(96, 38, 158)
            Case Else
                ws.Cells(r, 2).Interior.Color = RGB(220, 230, 242)
                ws.Cells(r, 2).Font.Color = RGB(30, 70, 120)
        End Select

        If amtDiff >= 1000# Then
            ws.Cells(r, 7).Font.Bold = True
            ws.Cells(r, 7).Interior.Color = RGB(255, 180, 180)
        End If
    Next r
End Sub

Sub FilterByAmountMismatch()
    Call FilterExceptionsByCategory("AMOUNT_MISMATCH")
End Sub

Sub FilterByMissingInLedger()
    Call FilterExceptionsByCategory("MISSING_IN_LEDGER")
End Sub

Sub FilterByMissingInBank()
    Call FilterExceptionsByCategory("MISSING_IN_BANK")
End Sub

Sub ClearAllExceptionFilters()
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Exceptions Breakdown")
    On Error GoTo 0
    If Not ws Is Nothing Then
        If ws.AutoFilterMode Then ws.ShowAllData
    End If
End Sub

Private Sub FilterExceptionsByCategory(catName As String)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Exceptions Breakdown")
    On Error GoTo 0
    If ws Is Nothing Then Exit Sub

    ws.Activate
    If ws.AutoFilterMode Then ws.ShowAllData
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    
    ws.Range("A1:H" & lastRow).AutoFilter Field:=2, Criteria1:="=" & catName
End Sub

Private Sub CreateDynamicFilters()
    Dim ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        If ws.FilterMode Then ws.ShowAllData
        Dim lastRow As Long
        Dim lastCol As Long
        lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
        lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
        If lastRow > 1 And lastCol > 1 Then
            ws.Range(ws.Cells(1, 1), ws.Cells(lastRow, lastCol)).AutoFilter
        End If
    Next ws
End Sub

Private Sub AutoFitAllSheets()
    Dim ws As Worksheet
    For Each ws In ThisWorkbook.Worksheets
        ws.Columns.AutoFit
    Next ws
End Sub
