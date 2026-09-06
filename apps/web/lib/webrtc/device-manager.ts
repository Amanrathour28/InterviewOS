import { MediaDeviceSettings } from './types';

export class DeviceManager {
  static async enumerateDevices(): Promise<MediaDeviceSettings> {
    if (typeof window === 'undefined' || !navigator.mediaDevices?.enumerateDevices) {
      return {
        selectedCameraId: '',
        selectedMicId: '',
        selectedSpeakerId: '',
        availableCameras: [],
        availableMics: [],
        availableSpeakers: [],
      };
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();

      const cameras = devices.filter((d) => d.kind === 'videoinput');
      const mics = devices.filter((d) => d.kind === 'audioinput');
      const speakers = devices.filter((d) => d.kind === 'audiooutput');

      return {
        selectedCameraId: cameras[0]?.deviceId || '',
        selectedMicId: mics[0]?.deviceId || '',
        selectedSpeakerId: speakers[0]?.deviceId || '',
        availableCameras: cameras,
        availableMics: mics,
        availableSpeakers: speakers,
      };
    } catch (err) {
      console.warn('[DeviceManager] Failed to enumerate devices:', err);
      return {
        selectedCameraId: '',
        selectedMicId: '',
        selectedSpeakerId: '',
        availableCameras: [],
        availableMics: [],
        availableSpeakers: [],
      };
    }
  }

  static async setAudioOutput(element: HTMLMediaElement, deviceId: string): Promise<boolean> {
    if (!element || typeof (element as any).setSinkId !== 'function') {
      return false;
    }

    try {
      await (element as any).setSinkId(deviceId);
      return true;
    } catch (err) {
      console.warn('[DeviceManager] Failed to set audio sink ID:', err);
      return false;
    }
  }

  static async checkPermissions(): Promise<{ camera: boolean; microphone: boolean }> {
    if (typeof window === 'undefined' || !navigator.permissions) {
      return { camera: true, microphone: true };
    }

    try {
      const camQuery = await navigator.permissions.query({ name: 'camera' as any }).catch(() => null);
      const micQuery = await navigator.permissions.query({ name: 'microphone' as any }).catch(() => null);

      return {
        camera: camQuery ? camQuery.state === 'granted' : true,
        microphone: micQuery ? micQuery.state === 'granted' : true,
      };
    } catch {
      return { camera: true, microphone: true };
    }
  }
}
