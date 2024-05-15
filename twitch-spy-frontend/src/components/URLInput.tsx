import React from "react";

export const URLInput = () => {
  const formID = "urlForm";
  const submitForm = (event: React.FormEvent) => {
    event.preventDefault();
    const formElement = document.getElementById(formID);
    if (formElement && formElement instanceof HTMLFormElement) {
      const formData = new FormData(formElement);
      fetch("/", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Server response:", data);
        });
    }
  };

  return (
    <div>
      <form id={formID} onSubmit={submitForm}>
        <textarea
          id="urlInput"
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
