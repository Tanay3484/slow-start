// The device's position, on the web and in the Android app. It never leaves the device (R6.2); only
// the centre of a ~1 km cell goes to OpenStreetMap, and only a cell id is stored.
import { Capacitor } from "@capacitor/core";

export interface Position {
  lat: number;
  lon: number;
}

export async function getPosition(): Promise<Position> {
  if (Capacitor.isNativePlatform()) {
    const { Geolocation } = await import("@capacitor/geolocation");
    const perm = await Geolocation.requestPermissions({ permissions: ["location"] });
    if (perm.location === "denied") throw new Error("Location permission was denied");
    const p = await Geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 15_000 });
    return { lat: p.coords.latitude, lon: p.coords.longitude };
  }
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("This browser cannot share a location"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
      (e) => reject(new Error(e.code === 1 ? "Location permission was denied" : "Could not find your location")),
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 },
    );
  });
}
