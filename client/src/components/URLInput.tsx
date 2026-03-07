import React, {useEffect, useRef, useState} from "react";
import {Socket} from "socket.io-client";
import {TextInputStats} from "./util/TextInputStats.tsx";
import {apiRequest} from "../backend/backend.ts";
import styles from "./URLInput.module.css";

interface URLInputProps {
    socket: Socket;
}

export const URLInput = ({socket}: URLInputProps) => {
    const [userInput, setUserInput] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [planning, setPlanning] = useState<{current: number; total: number} | null>(null);
    const formRef = useRef<HTMLFormElement>(null);

    useEffect(() => {
        const onPlanning = (data: {current: number; total: number}) => {
            setPlanning(data.total > 0 ? data : null);
        };
        socket.on("url_planning", onPlanning);
        return () => { socket.off("url_planning", onPlanning); };
    }, [socket]);

    const unwrapIfJsonArray = (input: string): string => {
        const trimmed = input.trim();
        if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
            try {
                const parsed = JSON.parse(trimmed);
                if (Array.isArray(parsed) && parsed.every((x) => typeof x === "string")) {
                    return parsed.join("\n");
                }
            } catch {
                // fall through to normal parsing
            }
        }
        return input;
    };

    const cleanInput = (input: string): string =>
        unwrapIfJsonArray(input)
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
        const urlList = unwrapIfJsonArray(input).replace(/\s+/g, ",").split(",");
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
                urls: cleanedInput,
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
            setPlanning(null);
        }
    };

    return (
        <form ref={formRef} onSubmit={submitForm} className={styles.form}>
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
                {planning ? (
                    <span className={styles.planningText}>
                        Planning {planning.current} / {planning.total}…
                    </span>
                ) : (
                    <TextInputStats urlCount={validUrlCount} inputValidity={rawInputValid} />
                )}
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
