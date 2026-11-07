export type DocumentSection = {
  title: string;
  paragraphs?: string[];
  bullets?: string[];
};

export type PageDocument = {
  title: string;
  description: string;
  lead: string;
  sections: DocumentSection[];
  /** Legal documents show the last-updated date and the draft notice. */
  legal?: boolean;
};
