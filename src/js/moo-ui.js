import Combobox from "./components/combobox.js";
import ContextMenu from "./components/context-menu.js";
import DataTable from "./components/datatable.js";
import Datepicker, {
  MooCalendar,
  MooDateRangePicker,
} from "./components/datepicker.js";
import Sidebar from "./components/sidebar.js";
import Slider from "./components/slider.js";
import TableOfContents from "./components/toc.js";
import OverlayScrollbar from "./components/overlay-scrollbar.js";
import { initSheets } from "./components/sheet.js";
import FloatingPanel from "./components/floating-panel.js";
import PasswordRequirements from "./password-requirements.js";

async function loadChart() {
  const { default: Chart } = await import("./chart.js");
  return Chart;
}

const MooUI = {
  PasswordRequirements,
  FloatingPanel,
  loadChart,
  Combobox,
  ContextMenu,
  DataTable,
  Datepicker,
  MooCalendar,
  MooDateRangePicker,
  Sidebar,
  Slider,
  TableOfContents,
  OverlayScrollbar,
  initSheets,
};

export {
  PasswordRequirements,
  FloatingPanel,
  loadChart,
  Combobox,
  ContextMenu,
  DataTable,
  Datepicker,
  MooCalendar,
  MooDateRangePicker,
  Sidebar,
  Slider,
  TableOfContents,
  OverlayScrollbar,
  initSheets,
};

export default MooUI;
