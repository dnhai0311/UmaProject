import { UmaCharacter, Scenario, SupportCard, Skill, Event, Choice } from '../types';

class DataService {
  private umaCharacters: UmaCharacter[] = [];
  private scenarios: Scenario[] = [];
  private supportCards: SupportCard[] = [];
  private skills: Skill[] = [];

  async loadAllData(): Promise<void> {
    try {
      const [umaData, scenarioData, supportData, skillsData] = await Promise.all([
        fetch('/data/all_uma_events.json').then(res => res.json()),
        fetch('/data/all_scenario_events.json').then(res => res.json()),
        fetch('/data/all_support_events.json').then(res => res.json()),
        fetch('/data/all_skills.json').then(res => res.json())
      ]);

      this.umaCharacters = umaData;
      this.scenarios = scenarioData;
      this.supportCards = supportData;
      this.skills = skillsData;
    } catch (error) {
      console.error('Error loading data:', error);
      throw error;
    }
  }

  getUmaCharacters(): UmaCharacter[] {
    return this.umaCharacters;
  }

  getScenarios(): Scenario[] {
    return this.scenarios;
  }

  getSupportCards(): SupportCard[] {
    return this.supportCards;
  }

  getSkills(): Skill[] {
    return this.skills;
  }

  searchUmaCharacters(query: string): UmaCharacter[] {
    const lowerQuery = query.toLowerCase();
    return this.umaCharacters.filter(character =>
      character.name.toLowerCase().includes(lowerQuery) ||
      character.rarity.toLowerCase().includes(lowerQuery)
    );
  }

  searchScenarios(query: string): Scenario[] {
    const lowerQuery = query.toLowerCase();
    return this.scenarios.filter(scenario =>
      scenario.name.toLowerCase().includes(lowerQuery)
    );
  }

  searchSupportCards(query: string, rarityFilter?: string): SupportCard[] {
    let filtered = this.supportCards;
    
    if (rarityFilter) {
      filtered = filtered.filter(card => 
        card.rarity.toLowerCase().includes(rarityFilter.toLowerCase())
      );
    }

    if (query) {
      const lowerQuery = query.toLowerCase();
      filtered = filtered.filter(card =>
        card.name.toLowerCase().includes(lowerQuery)
      );
    }

    return filtered;
  }

  searchSkills(query: string): Skill[] {
    const lowerQuery = query.toLowerCase();
    return this.skills.filter(skill =>
      skill.name.toLowerCase().includes(lowerQuery) ||
      skill.effect.toLowerCase().includes(lowerQuery)
    );
  }

  searchEvents(query: string): Array<{event: Event, source: string, sourceName: string, sourceImage?: string}> {
    const lowerQuery = query.toLowerCase();
    const results: Array<{event: Event, source: string, sourceName: string, sourceImage?: string}> = [];

    // Search in character events
    this.umaCharacters.forEach(character => {
      character.events.forEach(event => {
        if (event.event.toLowerCase().includes(lowerQuery)) {
          results.push({
            event,
            source: 'character',
            sourceName: character.name,
            sourceImage: character.imageUrl
          });
        }
      });
    });

    // Search in scenario events
    this.scenarios.forEach(scenario => {
      scenario.events.forEach(event => {
        if (event.event.toLowerCase().includes(lowerQuery)) {
          results.push({
            event,
            source: 'scenario',
            sourceName: scenario.name,
            sourceImage: scenario.imageUrl
          });
        }
      });
    });

    // Search in support card events
    this.supportCards.forEach(card => {
      card.trainingEvents.forEach(event => {
        if (event.event.toLowerCase().includes(lowerQuery)) {
          results.push({
            event,
            source: 'card',
            sourceName: card.name,
            sourceImage: card.imageUrl
          });
        }
      });
    });

    return results;
  }

  searchChoices(query: string): Array<{choice: Choice, event: Event, source: string, sourceName: string, sourceImage?: string}> {
    const lowerQuery = query.toLowerCase();
    const results: Array<{choice: Choice, event: Event, source: string, sourceName: string, sourceImage?: string}> = [];

    // Search in character events
    this.umaCharacters.forEach(character => {
      character.events.forEach(event => {
        event.choices.forEach(choice => {
          if (choice.choice.toLowerCase().includes(lowerQuery) || 
              choice.effect.toLowerCase().includes(lowerQuery)) {
            results.push({
              choice,
              event,
              source: 'character',
              sourceName: character.name,
              sourceImage: character.imageUrl
            });
          }
        });
      });
    });

    // Search in scenario events
    this.scenarios.forEach(scenario => {
      scenario.events.forEach(event => {
        event.choices.forEach(choice => {
          if (choice.choice.toLowerCase().includes(lowerQuery) || 
              choice.effect.toLowerCase().includes(lowerQuery)) {
            results.push({
              choice,
              event,
              source: 'scenario',
              sourceName: scenario.name,
              sourceImage: scenario.imageUrl
            });
          }
        });
      });
    });

    // Search in support card events
    this.supportCards.forEach(card => {
      card.trainingEvents.forEach(event => {
        event.choices.forEach(choice => {
          if (choice.choice.toLowerCase().includes(lowerQuery) || 
              choice.effect.toLowerCase().includes(lowerQuery)) {
            results.push({
              choice,
              event,
              source: 'card',
              sourceName: card.name,
              sourceImage: card.imageUrl
            });
          }
        });
      });
    });

    return results;
  }

  getRarities(): string[] {
    const rarities = new Set<string>();
    this.supportCards.forEach(card => {
      if (card.rarity) {
        rarities.add(card.rarity);
      }
    });
    return Array.from(rarities).sort();
  }
}

export const dataService = new DataService(); 