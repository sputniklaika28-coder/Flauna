import { BrowserRouter, Route, Routes } from "react-router-dom";
import Lobby from "./routes/Lobby";
import Room from "./routes/Room";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Lobby />} />
        <Route path="/room/:roomId" element={<Room />} />
      </Routes>
    </BrowserRouter>
  );
}
