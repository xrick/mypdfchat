import React from "react";
import ReactDOM from "react-dom/client";
import { withStreamlitConnection } from "streamlit-component-lib";
import RichTextArea from "./richTextArea";

const Connected = withStreamlitConnection(RichTextArea);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Connected />
  </React.StrictMode>
);

