import React, { useMemo } from "react";

interface TextInputStatsProps {
  value: string;
}

const isValidUrl = (url: string): boolean => {
  const validURLRegex =
    /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)/;
  return validURLRegex.test(url);
};

const isInputValid = (input: string): boolean => {
  const urlList = input.split(",");
  return urlList.every(isValidUrl);
};

export const TextInputStats: React.FC<TextInputStatsProps> = ({ value }) => {
  const urlCount = useMemo(() => value.split(",").length, [value]);
  const inputValidity = useMemo(() => isInputValid(value), [value]);

  return (
    <div>
      <h3>{urlCount}</h3>
      <h3 className={inputValidity ? "valid" : "invalid"}>
        Input is {inputValidity ? "valid" : "invalid"}
      </h3>
    </div>
  );
};

export default TextInputStats;
