import React, { useRef, useState } from "react";
import { TextInputStats } from "./util/TextInputStats";

export const URLInput = () => {
  const [userInput, setUserInput] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  const submitForm = (event: React.FormEvent) => {
    event.preventDefault();
    console.log("Text value:", userInput);
    if (formRef.current) {
      fetch("/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          urls: userInput,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Server response:", data);
        })
        .then(() => setUserInput(""));
    }
  };

  return (
    <div>
      <form ref={formRef} onSubmit={submitForm}>
        <textarea
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          rows={6}
          cols={60}
          placeholder="Enter URLs comma-separated..."
        ></textarea>
        <TextInputStats value={userInput} />
        <br />
        <button type="submit">Submit URLs for processing</button>
      </form>
    </div>
  );
};

export default URLInput;
