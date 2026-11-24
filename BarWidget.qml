pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui as Ui
import "Model.js" as Model

Ui.BarWidget {
  id: root
  moduleName: "mo.prayer"
  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }
  property var report: null
  property var pendingResult: null
  property string activeKey: ""
  property bool pendingRefresh: false
  property bool pendingForce: false
  property bool editing: false
  property bool popoutSwitching: false
  property bool popoutSwitchClosing: false
  property Ui.PanelController controller: Ui.PanelController {}
  readonly property bool opened: controller.open
  readonly property double now: clock.date.getTime() / 1000
  readonly property bool usable: Model.validReport(report) && now >= report.validFrom && now < report.validUntil
  readonly property var nextPrayer: usable ? Model.nextEvent(report, now) : null
  readonly property string requestKey: JSON.stringify(Model.requestSettings(root.settings))
  readonly property string countdown: nextPrayer ? duration(nextPrayer.start - now) : ""
  readonly property string barLabel: nextPrayer ? strings.t("barNext").arg(strings.t(nextPrayer.name)).arg(countdown) : ""
  readonly property real openPanelIndicatorWidth: barContent.implicitWidth
  readonly property var locale: Qt.locale(Commons.I18n.formatLocale)

  function duration(seconds) {
    var p = Model.remaining(seconds)
    return strings.t("duration").arg(Commons.I18n.formatNumber(p.hours)).arg(Commons.I18n.formatNumber(p.minutes))
  }
  function dateText(iso) {
    var months = []
    for (var i = 0; i < 12; i++) months.push(root.locale.standaloneMonthName(i, Locale.ShortFormat))
    return Model.displayDate(iso, months, Commons.I18n.formatNumber)
  }
  function timeText(epoch, showDay) {
    if (!usable || epoch === null) return "—"
    var c = report.clock[String(epoch)]
    var value = Model.formatTime(c, root.setting("hour24", false), Commons.I18n.formatNumber,
      root.locale.amText, root.locale.pmText)
    if (showDay && c && c.day > 0) return strings.t("nextDay").arg(value)
    if (showDay && c && c.day < 0) return strings.t("previousDay").arg(value)
    return value
  }
  function open() { controller.show() }
  function close() { controller.hide() }
  function toggle() { opened ? close() : open() }
  function closeForPopoutSwitch() {
    popoutSwitchClosing = true
    close()
    Qt.callLater(function() { root.popoutSwitchClosing = false })
  }
  function switchPanel(direction) {
    return root.bar && root.bar.switchPanelFrom ? root.bar.switchPanelFrom(root, direction) : false
  }
  function save(values) {
    if (JSON.stringify(Model.requestSettings(values)) === requestKey
        && values.hour24 === root.setting("hour24", false)) {
      root.editing = false
      return
    }
    var entry = Object.assign({}, root.settings, values, {id: root.moduleName})
    if (!root.bar || !root.bar.shell || !root.bar.shell.updateEntryInline(root.moduleName, entry)) {
      root.report = {schema: 2, ok: false, error: "save"}
      return
    }
    root.settings = entry
    root.editing = false
  }
  function refresh(force) {
    if (fetcher.running) {
      pendingRefresh = true
      pendingForce = pendingForce || force
      return
    }
    activeKey = requestKey
    pendingResult = null
    var helper = decodeURIComponent(Qt.resolvedUrl("fetch.py").toString().replace(/^file:\/\//, ""))
    // Settings can contain exact coordinates. Pass them on stdin, not argv.
    var args = ["python3", "-B", helper]
    if (force) args.push("--force")
    else if (!root.setting("autoRefresh", false)) args.push("--offline")
    fetcher.command = args
    fetcher.running = true
  }
  function forceRefresh() { refresh(true) }

  onRequestKeyChanged: {
    report = null
    pendingRefresh = false
    pendingForce = false
    if (!root.setting("autoRefresh", false) && fetcher.running) fetcher.running = false
    settingsDebounce.restart()
  }
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  SystemClock {
    id: clock
    precision: SystemClock.Minutes
    onDateChanged: if (root.report && root.report.ok && root.now >= root.report.validUntil) settingsDebounce.restart()
  }
  Timer {
    id: settingsDebounce
    interval: 400
    running: true
    onTriggered: root.refresh(false)
  }
  Timer {
    interval: 15 * 60 * 1000
    repeat: true
    running: root.setting("autoRefresh", false)
    onTriggered: root.refresh(false)
  }
  Process {
    id: fetcher
    stdinEnabled: true
    onStarted: fetcher.write(root.activeKey + "\n")
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (root.activeKey !== root.requestKey) return
        root.pendingResult = Model.parseResponse(text)
        root.report = root.pendingResult
      }
    }
    onExited: function(exitCode) {
      if (exitCode !== 0 && root.activeKey === root.requestKey)
        root.report = {schema: 2, ok: false, error: "network"}
      if (root.pendingRefresh) Qt.callLater(function() {
        var force = root.pendingForce
        root.pendingRefresh = false
        root.pendingForce = false
        root.refresh(force)
      })
      else Qt.callLater(function() {
        if (!fetcher.running && root.activeKey === root.requestKey && root.pendingResult === null)
          root.report = {schema: 2, ok: false, error: "response"}
      })
    }
  }
  ShellIpc {
    target: root.moduleName
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.toggle() }
    function refresh(): void { root.broadcast("forceRefresh") }
    function edit(): void { root.editing = true; root.open() }
    function status(): string {
      return JSON.stringify({opened: root.opened, ready: root.usable, loading: fetcher.running,
        date: root.usable ? root.dateText(root.report.date) : null,
        error: root.report && !root.report.ok ? root.report.error : null})
    }
  }

  Ui.WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    fixedWidth: root.vertical ? root.barSize : barContent.implicitWidth + Style.space(18)
    fixedHeight: root.vertical ? Style.bar.iconSlot : root.barSize
    tooltipText: ""
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: strings.t("title")
    Accessible.description: root.barLabel
    Keys.onReturnPressed: root.toggle()
    Keys.onSpacePressed: root.toggle()
    onPressed: function(b) {
      if (b === Qt.MiddleButton) root.forceRefresh()
      else if (b === Qt.RightButton) { root.editing = true; root.open() }
      else root.toggle()
    }
    Row {
      id: barContent
      anchors.centerIn: parent
      spacing: Style.space(7)
      scale: button.pressScale
      PrayerIcon {
        width: Style.bar.iconSize
        height: width
        foreground: button.foreground
        anchors.verticalCenter: parent.verticalCenter
      }
      PlainLabel {
        visible: !root.vertical && text !== ""
        text: root.barLabel
        color: button.foreground
        font.pixelSize: Style.font.body
        anchors.verticalCenter: parent.verticalCenter
      }
    }
  }
  Ui.KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: panel.loadedContent
    contentWidth: panel.fittedContentWidth(Style.space(480))
    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight)
    content: FocusScope {
      implicitHeight: column.implicitHeight
      Keys.onEscapePressed: function(event) {
        if (root.editing) root.editing = false
        else root.close()
        event.accepted = true
      }
      Flickable {
        id: scroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height
        Connections {
          target: root
          function onEditingChanged() { scroll.contentY = 0 }
        }
        Column {
          id: column
          width: parent.width
          spacing: Style.space(16)
          Row {
            width: parent.width
            spacing: Style.space(10)
            PrayerIcon {
              width: Style.space(30)
              height: width
              foreground: Commons.Color.accent
              anchors.verticalCenter: parent.verticalCenter
            }
            Column {
              width: Math.max(0, parent.width - Style.space(30) - refreshButton.width - settingsButton.width - parent.spacing * 3)
              spacing: Style.space(3)
              PlainLabel {
                width: parent.width
                text: strings.t("title")
                font.pixelSize: Style.font.title
                font.bold: true
                elide: Text.ElideRight
              }
              PlainLabel {
                width: parent.width
                text: root.usable ? root.dateText(root.report.date) : strings.t("subtitle")
                opacity: 0.6
                font.pixelSize: Style.font.caption
                elide: Text.ElideRight
              }
            }
            Ui.Button {
              id: refreshButton
              text: strings.t("refresh")
              enabled: !fetcher.running
              focusable: true
              anchors.verticalCenter: parent.verticalCenter
              onClicked: root.forceRefresh()
            }
            Ui.Button {
              id: settingsButton
              text: strings.t(root.editing ? "done" : "settings")
              selected: root.editing
              focusable: true
              anchors.verticalCenter: parent.verticalCenter
              onClicked: root.editing = !root.editing
            }
          }
          Loader {
            width: parent.width
            active: !root.editing
            visible: active
            height: item ? item.implicitHeight : 0
            sourceComponent: PrayerTimetable { host: root; translations: strings }
          }
          Loader {
            width: parent.width
            active: root.editing
            visible: active
            height: item ? item.implicitHeight : 0
            sourceComponent: PrayerSettings {
              initialSettings: root.settings
              translations: strings
              onApplied: function(values) { root.save(values) }
              onCancelled: root.editing = false
            }
          }
        }
      }
    }
  }
}
