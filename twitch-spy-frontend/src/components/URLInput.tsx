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

  const cleanInput = (input: string): string => {
    return input
      .split(",")
      .map((url) => url.trim())
      .join(",");
  };

  const isValidUrl = (url: string): boolean => {
    const validURLRegex =
      /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)/;
    return validURLRegex.test(url);
  };

  const isInputValid = (input: string): boolean => {
    const urlList = input.split(",");
    return urlList.every(isValidUrl);
  };

  const calcValidUrlCount = (input: string): number => {
    const urlList = input.split(",");
    return urlList.filter(isValidUrl).length;
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
        <TextInputStats
          urlCount={calcValidUrlCount(cleanInput(userInput))}
          inputValidity={isInputValid(cleanInput(userInput))}
        />
        <br />
        <button type="submit">Submit URLs for processing</button>
      </form>
    </div>
  );
};

export default URLInput;
