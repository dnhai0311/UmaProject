export interface Choice {
  choice: string;
  effect: string;
  skill?: {
    name: string;
    effect: string;
  };
  bond?: {
    name: string;
    effect: string;
  };
}

export interface Event {
  event: string;
  choices: Choice[];
}

export interface UmaCharacter {
  name: string;
  url_detail: string;
  imageUrl: string;
  rarity: string;
  events: Event[];
}

export interface Scenario {
  name: string;
  imageUrl?: string;
  events: Event[];
}

export interface SupportCard {
  name: string;
  url_detail: string;
  imageUrl: string;
  rarity: string;
  trainingEvents: Event[];
}

export interface Skill {
  imageUrl: string;
  name: string;
  effect: string;
} 