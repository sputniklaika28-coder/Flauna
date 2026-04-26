// Phase 8: full English translation
const en = {
  lobby: {
    title: "Lobby",
    createRoom: "Create Room",
    joinRoom: "Join Room",
    scenarioId: "Scenario ID",
    playerName: "Player Name",
    roomId: "Room ID",
    submit: "Confirm",
    creating: "Creating...",
    joining: "Joining...",
  },
  room: {
    title: "Session",
    connecting: "Connecting...",
    connected: "Connected",
    disconnected: "Disconnected",
    chat: {
      placeholder: "Say something...",
      send: "Send",
    },
  },
  errors: {
    roomNotFound: "Room not found",
    invalidToken: "Authentication token is invalid",
    connectionFailed: "Failed to connect",
    unknown: "An unexpected error occurred",
  },
} as const;

export default en;
