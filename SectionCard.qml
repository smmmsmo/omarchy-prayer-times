import QtQuick
import qs.Commons as Commons

Rectangle {
  id: root
  default property alias content: body.data
  property alias spacing: body.spacing
  property int padding: Commons.Style.space(14)
  implicitHeight: body.implicitHeight + padding * 2
  radius: Commons.Style.cornerRadius
  color: Qt.alpha(Commons.Color.popups.text, 0.035)
  border.width: 1
  border.color: Qt.alpha(Commons.Color.popups.text, 0.08)
  Column {
    id: body
    x: root.padding
    y: root.padding
    width: root.width - root.padding * 2
    spacing: Commons.Style.space(10)
  }
}
