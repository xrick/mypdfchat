import React, { useEffect, useRef, useState } from "react";
import { ComponentProps, Streamlit } from "streamlit-component-lib";
import "./styles.css";

const RichTextArea: React.FC<ComponentProps> = (props) => {
  const { args, disabled, theme } = props;

  const initialValue = (args["value"] ?? "") as string;
  const height = (args["height"] ?? 240) as number;
  const placeholder = (args["placeholder"] ?? "") as string;
  const showToolbar = (args["toolbar"] ?? true) as boolean;

  const [html, setHtml] = useState<string>(initialValue);
  const editorRef = useRef<HTMLDivElement | null>(null);

  // Keep internal state in sync if Streamlit updates the initial value
  useEffect(() => {
    setHtml(initialValue ?? "");
  }, [initialValue]);

  // Resize frame as content/props change
  useEffect(() => {
    const extra = showToolbar ? 44 : 0;
    Streamlit.setFrameHeight(height + extra + 24);
  }, [height, showToolbar, html]);

  // Push value to Streamlit whenever it changes
  useEffect(() => {
    Streamlit.setComponentValue(html);
  }, [html]);

  const onInput = () => {
    const content = editorRef.current?.innerHTML ?? "";
    setHtml(content);
  };

  const exec = (command: string, value?: string) => {
    if (disabled) return;
    editorRef.current?.focus();
    document.execCommand(command, false, value);
    onInput();
  };

  const onLink = () => {
    const url = window.prompt("Enter URL");
    if (url) exec("createLink", url);
  };

  const applyBlock = (tag: string) => exec("formatBlock", tag);

  return (
    <div className="rta-container" data-theme={theme?.base}>
      {showToolbar && (
        <div className="rta-toolbar">
          <button type="button" onClick={() => exec("bold")} title="Bold">
            <b>B</b>
          </button>
          <button type="button" onClick={() => exec("italic")} title="Italic">
            <i>I</i>
          </button>
          <button type="button" onClick={() => exec("underline")} title="Underline">
            <u>U</u>
          </button>
          <button
            type="button"
            onClick={() => exec("strikeThrough")}
            title="Strikethrough"
          >
            S
          </button>
          <span className="rta-sep" />
          <button type="button" onClick={() => applyBlock("H1")} title="Heading 1">
            H1
          </button>
          <button type="button" onClick={() => applyBlock("H2")} title="Heading 2">
            H2
          </button>
          <button type="button" onClick={() => applyBlock("P")} title="Paragraph">
            P
          </button>
          <span className="rta-sep" />
          <button
            type="button"
            onClick={() => exec("insertUnorderedList")}
            title="Bulleted list"
          >
            • List
          </button>
          <button
            type="button"
            onClick={() => exec("insertOrderedList")}
            title="Numbered list"
          >
            1. List
          </button>
          <span className="rta-sep" />
          <button type="button" onClick={onLink} title="Insert link">
            Link
          </button>
          <button
            type="button"
            onClick={() => exec("removeFormat")}
            title="Clear formatting"
          >
            Clear
          </button>
        </div>
      )}
      <div
        ref={editorRef}
        className="rta-editor"
        contentEditable={!disabled}
        onInput={onInput}
        style={{ height }}
        data-placeholder={placeholder}
        dangerouslySetInnerHTML={{ __html: html }}
        suppressContentEditableWarning
      />
    </div>
  );
};

export default RichTextArea;

