import type { ArtMeta, ArtName } from "../types";

export const ARTS: ArtMeta[] = [
  {
    name: "加護防壁",
    mp_cost: 2,
    target_type: "single",
    description:
      "味方1体を霊的な護りで包む。次のラウンド開始まで armor_value を一時的に+1。",
  },
  {
    name: "反閃歩法",
    mp_cost: 2,
    target_type: "self",
    description: "術者本人。このラウンド中、次の回避判定で追加ダイス+1。",
  },
  {
    name: "霊力放出",
    mp_cost: 3,
    target_type: "area",
    description:
      "術者中心、半径2マスの敵に体判定（NORMAL）失敗で1ラウンドのスタン。",
  },
  {
    name: "霊弾発射",
    mp_cost: 2,
    target_type: "single",
    description:
      "敵1体に霊（NORMAL）vs 命中で 1d6 の霊的ダメージ。装甲を貫通。",
  },
  {
    name: "呪祝詛詞",
    mp_cost: 3,
    target_type: "single",
    description: "敵1体の次ラウンドの行動判定難易度を1段階上昇させる。",
  },
  {
    name: "式神使役",
    mp_cost: 4,
    target_type: "none",
    description:
      "式神を1体召喚。隣接する敵の攻撃判定を1段階難化（1ラウンド）。",
  },
];

const ART_BY_NAME: Map<string, ArtMeta> = new Map(ARTS.map((a) => [a.name, a]));

export function getArt(name: ArtName): ArtMeta | undefined {
  return ART_BY_NAME.get(name);
}
