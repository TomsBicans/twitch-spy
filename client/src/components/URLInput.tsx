import React, {useRef, useState} from "react";
import {TextInputStats} from "./util/TextInputStats.tsx";
import {apiRequest} from "../backend/backend.ts";
import styles from "./URLInput.module.css";

export const URLInput = () => {
    const [userInput, setUserInput] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const formRef = useRef<HTMLFormElement>(null);

    const cleanInput = (input: string): string =>
        input
            .replace(/\s+/g, ",")
            .split(",")
            .map((url) => url.trim())
            .filter((url) => url !== "")
            .filter((url) => isValidUrl(url))
            .join(",");

    const isValidUrl = (url: string): boolean => {
        const validURLRegex =
            /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)/;
        return validURLRegex.test(url);
    };

    const isInputValid = (input: string): boolean => {
        const urlList = input.replace(/\s+/g, ",").split(",");
        if (urlList.some((url) => url.trim() === "")) {
            return false;
        }
        return urlList.every(isValidUrl);
    };

    const calcValidUrlCount = (input: string): number =>
        input.split(",").filter(isValidUrl).length;

    const cleanedInput = cleanInput(userInput);
    const cleanedInputValid = isInputValid(cleanedInput);
    const rawInputValid = isInputValid(userInput);
    const validUrlCount = calcValidUrlCount(cleanedInput);

    const submitForm = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!formRef.current || !rawInputValid) {
            return;
        }

        try {
            setIsSubmitting(true);
            const response = await apiRequest("form_submit.POST", {
                urls: userInput,
            });
            if (response.success) {
                setUserInput("");
            } else {
                console.error("Form submission failed:", response.message);
            }
        } catch (error) {
            console.error("An error occurred:", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <form ref={formRef} onSubmit={submitForm} className={styles.form}>
            <div className={styles.formHeader}>
                <div>
                    <h2 className={styles.heading}>Drop URLs &amp; let them flow</h2>
                    <p className={styles.description}>
                        Paste track or playlist links. We tidy, validate, and queue them
                        automatically.
                    </p>
                </div>
            </div>
            <label className={styles.inputShell}>
                <span className={styles.inputLabel}>Paste URLs</span>
                <textarea
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    rows={userInput.length > 0 ? 8 : 6}
                    placeholder="Comma or line separated links — YouTube, SoundCloud, Bandcamp..."
                    className={styles.urlInput}
                />
                <span className={styles.inputGlow} aria-hidden="true" />
            </label>
            <div className={styles.metaRow}>
                <TextInputStats urlCount={validUrlCount} inputValidity={rawInputValid} />
                <div className={styles.buttonGroup}>
                    <button
                        type="button"
                        onClick={() => setUserInput(cleanedInput)}
                        disabled={!cleanedInputValid || cleanedInput === userInput}
                        className={styles.secondaryButton}
                    >
                        Clean input
                    </button>
                    <button
                        type="submit"
                        disabled={!rawInputValid || isSubmitting}
                        className={styles.primaryButton}
                    >
                        {isSubmitting ? "Submitting…" : "Queue downloads"}
                    </button>
                </div>
            </div>
        </form>
    );
};

export default URLInput;
