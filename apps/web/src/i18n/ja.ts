const ja = {
  lobby: {
    title: "ロビー",
    createRoom: "ルームを作成",
    joinRoom: "ルームに参加",
    scenarioId: "シナリオID",
    playerName: "プレイヤー名",
    roomId: "ルームID",
    submit: "決定",
    creating: "作成中...",
    joining: "参加中...",
  },
  room: {
    title: "セッション",
    connecting: "接続中...",
    connected: "接続済み",
    disconnected: "切断",
    chat: {
      placeholder: "発言する...",
      send: "送信",
    },
  },
  errors: {
    roomNotFound: "ルームが見つかりません",
    invalidToken: "認証トークンが無効です",
    connectionFailed: "接続に失敗しました",
    unknown: "予期しないエラーが発生しました",
  },
} as const;

export default ja;
export type TranslationKeys = typeof ja;
