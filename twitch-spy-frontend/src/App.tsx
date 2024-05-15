import React, { useEffect, useState } from "react";
import io from "socket.io-client";
import "./App.css";
import URLInput from "./components/URLInput";
import JobList from "./components/JobList";
import JobOverview from "./components/JobOverview";

const socket = io("localhost:5000"); // Socket to backend

const App: React.FC = () => {
  return (
    <div className="App">
      <h1>twitch-spy-music panel</h1>
      <URLInput />
      <JobOverview socket={socket} />
      <JobList socket={socket} />
    </div>
  );
};

export default App;
