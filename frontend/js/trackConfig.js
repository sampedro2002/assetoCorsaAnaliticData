/**
 * Track Configuration Registry
 * Defines static map properties for known tracks.
 * 
 * Each entry key MUST match the internal track name from Assetto Corsa.
 * 
 * Properties:
 * - image: Path to the map image relative to frontend root
 * - bounds: [minX, minZ, maxX, maxZ] (World coordinates from map.ini)
 *           Used or manual fallback calibration if map.ini is missing.
 */

const TRACK_CONFIG = {
    // Example for Silverstone National
    // Dynamic configuration:
    // The system automatically attempts to load:
    // /static/assets/tracks/[track_name]_[layout].png

    // You can add specific overrides here if needed, 
    // but by default it works for all imported maps.

    // Generic fallback for any other track
    'default': {
        image: '/static/assets/tracks/default.png'
    }
};

/**
 * Helper to get track config safely
 */
function getTrackConfig(trackName) {
    // Normalize track name (sometimes comes with layout like track@layout)
    let cleanName = trackName;
    // Normalize track name (track@layout -> track_layout)
    if (cleanName.includes('@')) {
        cleanName = cleanName.replace('@', '_');
    }

    // Try exact match
    if (TRACK_CONFIG[cleanName]) {
        return TRACK_CONFIG[cleanName];
    }

    // Start guessing or dynamic path
    // Default assumption: Image exists at standard path
    return {
        image: `/static/assets/tracks/${cleanName}.png`
    };
}
