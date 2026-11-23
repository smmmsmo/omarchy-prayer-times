import QtQuick

// Original, font-independent mosque mark. Repaints only on size/palette changes.
Canvas {
  id: root
  property color foreground: "white"
  implicitWidth: 24
  implicitHeight: 24
  antialiasing: true
  onForegroundChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()
  onPaint: {
    var ctx = getContext("2d")
    ctx.reset()
    ctx.scale(width / 24, height / 24)
    ctx.strokeStyle = foreground
    ctx.fillStyle = foreground
    ctx.lineWidth = 1.5
    ctx.lineCap = "round"
    ctx.lineJoin = "round"
    // Central dome and arched doorway.
    ctx.beginPath()
    ctx.moveTo(7, 13)
    ctx.bezierCurveTo(7, 10, 10.5, 8.5, 12, 6.5)
    ctx.bezierCurveTo(13.5, 8.5, 17, 10, 17, 13)
    ctx.closePath()
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(7, 15); ctx.lineTo(7, 20); ctx.lineTo(17, 20); ctx.lineTo(17, 15)
    ctx.moveTo(10, 20); ctx.lineTo(10, 17.5)
    ctx.bezierCurveTo(10, 15.5, 14, 15.5, 14, 17.5); ctx.lineTo(14, 20)
    // Symmetric minarets; generous negative space reads at bar sizes.
    ctx.moveTo(3.5, 20); ctx.lineTo(3.5, 9)
    ctx.moveTo(20.5, 20); ctx.lineTo(20.5, 9)
    ctx.moveTo(2, 9); ctx.lineTo(3.5, 6); ctx.lineTo(5, 9)
    ctx.moveTo(19, 9); ctx.lineTo(20.5, 6); ctx.lineTo(22, 9)
    ctx.moveTo(2, 20); ctx.lineTo(22, 20)
    ctx.stroke()
    // Small crescent, drawn with curves (no emoji or theme-specific font).
    ctx.beginPath()
    ctx.moveTo(13, 2)
    ctx.bezierCurveTo(10.3, 1.8, 10.2, 5.4, 13, 5.2)
    ctx.bezierCurveTo(11.6, 4.4, 11.6, 2.8, 13, 2)
    ctx.fill()
  }
}
