import React, { useRef, useState } from "react";

export const URLInput = () => {
  const [textValue, setTextValue] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  const submitForm = (event: React.FormEvent) => {
    event.preventDefault();
    console.log("Text value:", textValue);
    if (formRef.current) {
      fetch("/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          urls: textValue,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Server response:", data);
        });
    }
  };

  return (
    <div>
      <form ref={formRef} onSubmit={submitForm}>
        <textarea
          value={textValue}
          onChange={(e) => setTextValue(e.target.value)}
          rows={2}
          cols={20}
          placeholder="Enter URLs comma-separated..."
        ></textarea>
        <br />
        <button type="submit">Submit URLs for processing</button>
      </form>
    </div>
  );
};

export default URLInput;
