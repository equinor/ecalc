import {createContext, useContext} from 'react';

/** Number of spaces per indentation level, or undefined when guides are disabled. */
const IndentGuidesContext = createContext<number | undefined>(undefined);

export const IndentGuidesProvider = IndentGuidesContext.Provider;

export function useIndentGuides(): number | undefined {
  return useContext(IndentGuidesContext);
}
