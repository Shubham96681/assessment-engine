/** Default shared “Books” folder for local testing (override with VITE_RESOURCES_LIBRARY_URL). */
export const DEFAULT_RESOURCES_LIBRARY_FOLDER_URL =
  'https://drive.google.com/drive/folders/1lEKafXtOg3-dAxrgK9LCiVi3xxgrGAdi?usp=drive_link'

export function resourcesLibraryFolderUrl(): string {
  const fromEnv = import.meta.env.VITE_RESOURCES_LIBRARY_URL?.trim()
  return fromEnv || DEFAULT_RESOURCES_LIBRARY_FOLDER_URL
}
