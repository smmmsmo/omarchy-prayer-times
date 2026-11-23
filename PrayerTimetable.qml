pragma ComponentBehavior: Bound

import QtQuick
import qs.Commons as Commons
import qs.Ui as Ui
import "Model.js" as Model

Column {
  id: root
  required property var host
  required property var translations
  readonly property var report: host.report
  readonly property bool usable: host.usable
  spacing: Commons.Style.space(14)

  PlainLabel {
    width: parent.width
    visible: !root.usable
    text: root.translations.t(root.host.report === null ? "loading" :
      "error." + (root.host.report.error || "offline"))
    wrapMode: Text.WordWrap
    opacity: 0.75
  }
  Ui.Button {
    visible: !root.usable
    text: root.translations.t("configure")
    bordered: true
    focusable: true
    onClicked: root.host.editing = true
  }
  Column {
    width: parent.width
    visible: root.usable
    spacing: Commons.Style.space(14)
    SectionCard {
      width: parent.width
      PlainLabel {
        width: parent.width
        text: root.usable ? root.report.location : ""
        opacity: 0.65
        font.pixelSize: Commons.Style.font.bodySmall
        elide: Text.ElideRight
      }
      Row {
        width: parent.width
        spacing: Commons.Style.space(12)
        Column {
          width: (parent.width - parent.spacing) * 0.6
          spacing: Commons.Style.space(4)
          PlainLabel {
            text: root.translations.t("nextPrayer")
            opacity: 0.75
            font.pixelSize: Commons.Style.font.caption
          }
          PlainLabel {
            width: parent.width
            text: root.host.nextPrayer ? root.translations.t(root.host.nextPrayer.name) : "—"
            color: Commons.Color.accent
            font.pixelSize: Commons.Style.font.display
            font.bold: true
            elide: Text.ElideRight
          }
        }
        Column {
          width: (parent.width - parent.spacing) * 0.4
          spacing: Commons.Style.space(4)
          PlainLabel {
            text: root.host.nextPrayer ? root.host.timeText(root.host.nextPrayer.start, true) : "—"
            font.pixelSize: Commons.Style.font.title
            font.bold: true
          }
          PlainLabel {
            text: root.host.nextPrayer ? root.translations.t("inDuration").arg(root.host.countdown) : ""
            opacity: 0.65
            font.pixelSize: Commons.Style.font.caption
          }
        }
      }
      PlainLabel {
        text: root.usable ? root.report.timezone : ""
        font.pixelSize: Commons.Style.font.caption
        opacity: 0.7
      }
    }
    PlainLabel {
      visible: root.usable && root.report.offline
      width: parent.width
      text: root.translations.t("cached")
      font.pixelSize: Commons.Style.font.caption
      opacity: 0.65
      wrapMode: Text.WordWrap
    }
    PlainLabel {
      visible: root.usable && root.report.warnings.length > 0
      width: parent.width
      text: root.translations.t(root.usable && root.report.warnings.indexOf("solar") >= 0 ? "solarWarning" : "windowWarning")
      font.pixelSize: Commons.Style.font.caption
      wrapMode: Text.WordWrap
    }
    Column {
      width: parent.width
      spacing: Commons.Style.space(5)
      Row {
        width: parent.width
        Repeater {
          model: ["prayer", "start", "end"]
          PlainLabel {
            required property string modelData
            width: root.width / 3
            text: root.translations.t(modelData)
            font.pixelSize: Commons.Style.font.caption
            opacity: 0.72
          }
        }
      }
      Repeater {
        model: root.usable ? root.report.rows : []
        Rectangle {
          required property var modelData
          width: parent.width
          height: Commons.Style.space(37)
          radius: Commons.Style.cornerRadius
          readonly property bool current: modelData.start !== null && modelData.end !== null
            && modelData.start <= root.host.now && root.host.now < modelData.end
          color: current ? Qt.alpha(Commons.Color.accent, 0.12) : "transparent"
          Row {
            anchors.fill: parent
            PlainLabel {
              width: parent.width / 3
              anchors.verticalCenter: parent.verticalCenter
              text: root.translations.t(modelData.name)
              font.bold: true
            }
            PlainLabel {
              width: parent.width / 3
              anchors.verticalCenter: parent.verticalCenter
              text: root.host.timeText(modelData.start, true)
              font.pixelSize: Commons.Style.font.bodySmall
            }
            PlainLabel {
              width: parent.width / 3
              anchors.verticalCenter: parent.verticalCenter
              text: root.host.timeText(modelData.end, true)
              font.pixelSize: Commons.Style.font.bodySmall
              opacity: 0.75
            }
          }
        }
      }
    }
    SectionCard {
      width: parent.width
      PlainLabel {
        text: root.translations.t("fasting")
        font.pixelSize: Commons.Style.font.caption
        opacity: 0.6
      }
      Row {
        width: parent.width
        Repeater {
          model: ["sehri", "iftar"]
          Column {
            required property string modelData
            width: (root.width - Commons.Style.space(28)) / 2
            spacing: Commons.Style.space(6)
            PlainLabel {
              text: root.translations.t(modelData)
              opacity: 0.7
              font.pixelSize: Commons.Style.font.bodySmall
            }
            PlainLabel {
              text: root.usable ? root.host.timeText(root.report[modelData], true) : "—"
              font.pixelSize: Commons.Style.font.title
              font.bold: true
            }
            PlainLabel {
              text: root.usable ? root.translations.t("tomorrow").arg(root.host.timeText(
                modelData === "sehri" ? root.report.tomorrowSehri : root.report.tomorrowIftar, false)) : ""
              font.pixelSize: Commons.Style.font.caption
              opacity: 0.7
            }
          }
        }
      }
    }
    Row {
      width: parent.width
      Repeater {
        model: ["sunrise", "sunset"]
        Column {
          required property string modelData
          width: root.width / 2
          spacing: Commons.Style.space(4)
          PlainLabel {
            text: root.translations.t(modelData)
            font.pixelSize: Commons.Style.font.caption
            opacity: 0.7
          }
          PlainLabel { text: root.usable ? root.host.timeText(root.report[modelData], true) : "—" }
        }
      }
    }
    PlainLabel {
      width: parent.width
      text: root.translations.t("source")
      font.pixelSize: Commons.Style.font.caption
      opacity: 0.7
      wrapMode: Text.WordWrap
    }
  }
}
