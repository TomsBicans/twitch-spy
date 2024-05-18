import React from "react";
import "./TextInputStats.css";

interface TextInputStatsProps {
  urlCount: number;
  inputValidity: boolean;
}

export const TextInputStats: React.FC<TextInputStatsProps> = ({
  urlCount,
  inputValidity,
}) => {
  return (
    <div>
      <h3>
        {urlCount} valid URL{urlCount === 1 ? "" : "s"}
      </h3>
      {}
      <h3 className={inputValidity ? "valid" : "invalid"}>
        Input is {inputValidity ? "valid" : "invalid"}
      </h3>
    </div>
  );
};

export default TextInputStats;
