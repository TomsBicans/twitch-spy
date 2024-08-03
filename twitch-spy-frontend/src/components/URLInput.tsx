import React, { useRef, useState } from "react";
import { TextInputStats } from "./util/TextInputStats";
import { apiRequest } from "../backend/backend";
import styles from "./URLInput.module.css";

export const URLInput = () => {
  const [userInput, setUserInput] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  const submitForm = async (event: React.FormEvent) => {
    event.preventDefault();
    console.log("Text value:", userInput);
    if (formRef.current) {
      try {
        const response = await apiRequest("form_submit.POST", {
          urls: userInput,
        });
        console.log("Server response:", response);
        if (response.success) {
          setUserInput("");
        } else {
          console.error("Form submission failed:", response.message);
        }
      } catch (error) {
        console.error("An error occurred:", error);
      }
    }
  };

  const cleanInput = (input: string): string => {
    return input
      .replace(/\s+/g, ",")
      .split(",")
      .map((url) => url.trim())
      .filter((url) => url !== "")
      .filter((url) => isValidUrl(url))
      .join(",");
  };

  const isValidUrl = (url: string): boolean => {
    const validURLRegex =
      /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)/;
    return validURLRegex.test(url);
  };

  const isInputValid = (input: string): boolean => {
    const urlList = input.replace(/\s+/g, ",").split(",");
    // No empty URLs allowed
    if (urlList.some((url) => url.trim() === "")) {
      return false;
    }
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
          className={styles.urlInput}
        />
        <TextInputStats
          urlCount={calcValidUrlCount(cleanInput(userInput))}
          inputValidity={isInputValid(userInput)}
        />
        <>
          <button
            onClick={() => setUserInput(cleanInput(userInput))}
            disabled={!isInputValid(cleanInput(userInput))}
            className={styles.button}
          >
            Fix input
          </button>
          <br />
        </>
        <br />
        <button
          type="submit"
          disabled={!isInputValid(userInput)}
          className={styles.button}
        >
          Submit URLs for processing
        </button>
      </form>
    </div>
  );
};

export default URLInput;
