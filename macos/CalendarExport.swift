// Read-only EventKit bridge. It deliberately contains no save or remove calls.
import EventKit
import Foundation

struct EventRow: Encodable {
    let key: String
    let calendar_key: String
    let title: String
    let start: String
    let end: String
    let all_day: Bool
}

struct EventResult: Encodable {
    let complete: Bool
    let events: [EventRow]
}

struct CalendarRow: Encodable {
    let id: String
    let title: String
    let source: String
}

@main
struct CalendarExport {
    static func main() async {
        do {
            try await run()
        } catch {
            fputs("Calendar read failed: \(error)\n", stderr)
            exit(1)
        }
    }

    static func run() async throws {
        let store = EKEventStore()
        let status = EKEventStore.authorizationStatus(for: .event)
        if status == .notDetermined {
            guard try await store.requestFullAccessToEvents() else {
                throw NSError(domain: "CalendarExport", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "Calendar access denied"])
            }
        } else if status != .fullAccess && status != .authorized {
            throw NSError(domain: "CalendarExport", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Full Calendar read access is needed"])
        }

        let args = Array(CommandLine.arguments.dropFirst())
        let calendars = store.calendars(for: .event)
        if args.first == "--list" {
            let rows = calendars.map { CalendarRow(id: $0.calendarIdentifier,
                                                   title: $0.title,
                                                   source: $0.source.title) }
            try output(rows)
            return
        }
        guard args.count >= 4, args[0] == "--events" else {
            throw NSError(domain: "CalendarExport", code: 3,
                          userInfo: [NSLocalizedDescriptionKey: "Use --list or --events START END CALENDAR_ID..."])
        }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let fallback = ISO8601DateFormatter()
        guard let start = formatter.date(from: args[1]) ?? fallback.date(from: args[1]),
              let end = formatter.date(from: args[2]) ?? fallback.date(from: args[2]),
              end > start else {
            throw NSError(domain: "CalendarExport", code: 4,
                          userInfo: [NSLocalizedDescriptionKey: "Invalid date range"])
        }
        let selected = Set(args.dropFirst(3))
        let matched = calendars.filter { selected.contains($0.calendarIdentifier) }
        guard matched.count == selected.count else {
            throw NSError(domain: "CalendarExport", code: 5,
                          userInfo: [NSLocalizedDescriptionKey: "A selected calendar is unavailable"])
        }
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: matched)
        let events = store.events(matching: predicate)
        let rows = events.map { event -> EventRow in
            let calendarKey = event.calendar.calendarIdentifier
            let itemKey = event.calendarItemExternalIdentifier ?? event.eventIdentifier ?? "unknown"
            let occurrence = event.occurrenceDate.map { fallback.string(from: $0) } ?? "single"
            return EventRow(key: "\(calendarKey):\(itemKey):\(occurrence)",
                            calendar_key: calendarKey,
                            title: event.title ?? "Untitled event",
                            start: fallback.string(from: event.startDate),
                            end: fallback.string(from: event.endDate),
                            all_day: event.isAllDay)
        }
        try output(EventResult(complete: true, events: rows))
    }

    static func output<T: Encodable>(_ value: T) throws {
        let encoder = JSONEncoder()
        let data = try encoder.encode(value)
        FileHandle.standardOutput.write(data)
    }
}
