import { Socket } from 'socket.io';
import { SocketUser } from '../types/index.js';

export class RoomManager {
  static getPublicRoom(sessionId: string): string {
    return `interview:${sessionId}:public`;
  }

  static getInterviewerRoom(sessionId: string): string {
    return `interview:${sessionId}:interviewer`;
  }

  static getUserRoom(sessionId: string, userId: string): string {
    return `interview:${sessionId}:user:${userId}`;
  }

  static async joinRooms(socket: Socket, user: SocketUser): Promise<void> {
    const publicRoom = this.getPublicRoom(user.sessionId);
    await socket.join(publicRoom);

    // Join user-specific signaling room
    const userRoom = this.getUserRoom(user.sessionId, user.userId);
    await socket.join(userRoom);

    if (user.isInterviewer) {
      const interviewerRoom = this.getInterviewerRoom(user.sessionId);
      await socket.join(interviewerRoom);
      console.log(`[RoomManager] User ${user.userName} (${user.role}) joined public, user, & interviewer rooms for session ${user.sessionId}`);
    } else {
      console.log(`[RoomManager] Candidate ${user.userName} joined public & user rooms for session ${user.sessionId}`);
    }
  }

  static async leaveRooms(socket: Socket, user: SocketUser): Promise<void> {
    const publicRoom = this.getPublicRoom(user.sessionId);
    await socket.leave(publicRoom);

    const userRoom = this.getUserRoom(user.sessionId, user.userId);
    await socket.leave(userRoom);

    if (user.isInterviewer) {
      const interviewerRoom = this.getInterviewerRoom(user.sessionId);
      await socket.leave(interviewerRoom);
    }
  }
}
