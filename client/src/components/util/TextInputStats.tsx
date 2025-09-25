import React from "react";
import styles from "./TextInputStats.module.css";

interface TextInputStatsProps {
  urlCount: number;
  inputValidity: boolean;
}

export const TextInputStats: React.FC<TextInputStatsProps> = ({
    urlCount,
    inputValidity,
}) => {
    return (
        <div className={styles.statsContainer}>
            <div className={styles.countBlock}>
                <span className={styles.countValue}>{urlCount}</span>
                <span className={styles.countLabel}>
                    valid URL{urlCount === 1 ? "" : "s"}
                </span>
            </div>
            <span
                className={`${styles.validationChip} ${
                    inputValidity ? styles.valid : styles.invalid
                }`}
            >
                {inputValidity ? "Good to submit" : "Needs valid URLs"}
            </span>
        </div>
    );
};

export default TextInputStats;
