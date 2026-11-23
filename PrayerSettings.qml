pragma ComponentBehavior: Bound

import QtQuick
import qs.Commons as Commons
import qs.Ui as Ui
import "Model.js" as Model

Column {
  id: root
  required property var initialSettings
  required property var translations
  property var draft: Object.assign({}, Model.requestSettings(initialSettings),
    {hour24: initialSettings.hour24 === true})
  property string page: "location"
  signal applied(var values)
  signal cancelled()
  spacing: Commons.Style.space(14)

  function set(key, value) {
    var next = Object.assign({}, draft)
    next[key] = value
    draft = next
  }
  readonly property bool validLocation: draft.locationMode === "auto"
    || (draft.locationMode === "manual" && draft.city.trim() !== "" && draft.country.trim() !== "")
    || (draft.locationMode === "coordinates" && String(draft.latitude).trim() !== ""
      && String(draft.longitude).trim() !== "" && isFinite(Number(draft.latitude))
      && isFinite(Number(draft.longitude)) && Math.abs(Number(draft.latitude)) <= 90
      && Math.abs(Number(draft.longitude)) <= 180)

  Row {
    width: parent.width
    spacing: Commons.Style.space(5)
    Repeater {
      model: ["location", "calculation", "display"]
      Ui.Button {
        required property string modelData
        width: (root.width - Commons.Style.space(10)) / 3
        text: root.translations.t("tab." + modelData)
        selected: root.page === modelData
        bordered: true
        focusable: true
        onClicked: root.page = modelData
      }
    }
  }
  Ui.Dropdown {
    visible: root.page === "location"
    width: parent.width
    label: root.translations.t("locationMode")
    value: root.draft.locationMode
    options: [
      {value: "auto", label: root.translations.t("autoLocation")},
      {value: "manual", label: root.translations.t("manualLocation")},
      {value: "coordinates", label: root.translations.t("coordinateLocation")}
    ]
    onChanged: function(value) { root.set("locationMode", value) }
  }
  PlainLabel {
    visible: root.page === "location" && root.draft.locationMode === "auto"
    width: parent.width
    text: root.translations.t("ipHint")
    font.pixelSize: Commons.Style.font.caption
    opacity: 0.6
    wrapMode: Text.WordWrap
  }
  Column {
    visible: root.page === "location" && root.draft.locationMode === "manual"
    width: parent.width
    spacing: Commons.Style.space(8)
    Repeater {
      model: ["city", "state", "country"]
      Ui.TextField {
        required property string modelData
        width: parent.width
        text: root.draft[modelData] || ""
        placeholderText: root.translations.t(modelData)
        maximumLength: 100
        onTextEdited: root.set(modelData, text)
      }
    }
  }
  Column {
    visible: root.page === "location" && root.draft.locationMode === "coordinates"
    width: parent.width
    spacing: Commons.Style.space(8)
    Repeater {
      model: ["locationName", "latitude", "longitude"]
      Ui.TextField {
        required property string modelData
        width: parent.width
        text: String(root.draft[modelData] ?? "")
        placeholderText: root.translations.t(modelData)
        maximumLength: 100
        onTextEdited: root.set(modelData, text)
      }
    }
    PlainLabel {
      width: parent.width
      text: root.translations.t("coordinateHint")
      wrapMode: Text.WordWrap
      opacity: 0.6
      font.pixelSize: Commons.Style.font.caption
    }
  }
  Ui.Dropdown {
    visible: root.page === "calculation"
    width: parent.width
    label: root.translations.t("method")
    value: String(root.draft.method)
    options: Model.methodOptions(function(key) { return root.translations.t(key) })
    onChanged: function(value) { root.set("method", value === "auto" ? value : Number(value)) }
  }
  Ui.Dropdown {
    visible: root.page === "calculation"
    width: parent.width
    label: root.translations.t("school")
    value: String(root.draft.school)
    options: [
      {value: "0", label: root.translations.t("standard")},
      {value: "1", label: root.translations.t("hanafi")}
    ]
    onChanged: function(value) { root.set("school", Number(value)) }
  }
  Ui.Dropdown {
    visible: root.page === "calculation"
    width: parent.width
    label: root.translations.t("highLatitude")
    value: String(root.draft.highLatitude)
    options: [
      {value: "3", label: root.translations.t("angleBased")},
      {value: "1", label: root.translations.t("middleNight")},
      {value: "2", label: root.translations.t("oneSeventh")},
      {value: "0", label: root.translations.t("noAdjustment")}
    ]
    onChanged: function(value) { root.set("highLatitude", Number(value)) }
  }
  Ui.Dropdown {
    visible: root.page === "calculation" && String(root.draft.method) === "15"
    width: parent.width
    label: root.translations.t("shafaq")
    value: root.draft.shafaq
    options: [
      {value: "general", label: root.translations.t("generalTwilight")},
      {value: "ahmer", label: root.translations.t("redTwilight")},
      {value: "abyad", label: root.translations.t("whiteTwilight")}
    ]
    onChanged: function(value) { root.set("shafaq", value) }
  }
  Ui.Dropdown {
    visible: root.page === "calculation"
    width: parent.width
    label: root.translations.t("ishaEnd")
    value: root.draft.ishaEnd
    options: [
      {value: "midnight", label: root.translations.t("halfNight")},
      {value: "fajr", label: root.translations.t("nextFajr")}
    ]
    onChanged: function(value) { root.set("ishaEnd", value) }
  }
  PlainLabel {
    visible: root.page === "calculation"
    width: parent.width
    text: root.translations.t(root.draft.ishaEnd === "midnight" ? "midnightNote" : "fajrNote")
    wrapMode: Text.WordWrap
    font.pixelSize: Commons.Style.font.caption
    opacity: 0.6
  }
  PlainLabel {
    visible: root.page === "calculation"
    text: root.translations.t("offsets")
    font.bold: true
  }
  Row {
    visible: root.page === "calculation"
    width: parent.width
    spacing: Commons.Style.space(5)
    Repeater {
      model: Model.prayerNames
      Ui.NumberField {
        required property string modelData
        label: root.translations.t(modelData)
        width: (root.width - Commons.Style.space(20)) / 5
        fieldWidth: width
        from: -30
        to: 30
        value: root.draft.offsets[modelData] || 0
        onModified: function(value) {
          var next = Object.assign({}, root.draft.offsets)
          next[modelData] = value
          root.set("offsets", next)
        }
      }
    }
  }
  Ui.Toggle {
    visible: root.page === "display"
    width: parent.width
    label: root.translations.t("hour24")
    checked: root.draft.hour24
    onClicked: root.set("hour24", !checked)
  }
  Ui.Toggle {
    visible: root.page === "display" || root.page === "location"
    width: parent.width
    label: root.translations.t("autoRefresh")
    checked: root.draft.autoRefresh
    onClicked: root.set("autoRefresh", !checked)
  }
  PlainLabel {
    visible: root.page === "location"
    width: parent.width
    text: root.translations.t("networkNote")
    wrapMode: Text.WordWrap
    font.pixelSize: Commons.Style.font.caption
    opacity: 0.6
  }
  PlainLabel {
    visible: root.page === "calculation"
    width: parent.width
    text: root.translations.t("note")
    wrapMode: Text.WordWrap
    font.pixelSize: Commons.Style.font.caption
    opacity: 0.6
  }
  Row {
    spacing: Commons.Style.space(10)
    Ui.Button {
      text: root.translations.t("apply")
      enabled: root.validLocation
      selected: true
      bordered: true
      focusable: true
      onClicked: root.applied(root.draft)
    }
    Ui.Button {
      text: root.translations.t("cancel")
      focusable: true
      onClicked: root.cancelled()
    }
  }
}
