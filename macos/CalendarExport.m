// Read-only EventKit exporter. No save, remove, or calendar mutation calls.
#import <Foundation/Foundation.h>
#import <EventKit/EventKit.h>

static void fail(NSString *message) {
    fprintf(stderr, "Calendar read failed: %s\n", message.UTF8String);
    exit(1);
}

static NSDate *parseDate(NSString *value) {
    NSISO8601DateFormatter *formatter = [NSISO8601DateFormatter new];
    formatter.formatOptions = NSISO8601DateFormatWithInternetDateTime | NSISO8601DateFormatWithFractionalSeconds;
    NSDate *date = [formatter dateFromString:value];
    if (date) return date;
    formatter.formatOptions = NSISO8601DateFormatWithInternetDateTime;
    return [formatter dateFromString:value];
}

static NSString *formatDate(NSDate *date) {
    NSISO8601DateFormatter *formatter = [NSISO8601DateFormatter new];
    formatter.timeZone = [NSTimeZone timeZoneForSecondsFromGMT:0];
    formatter.formatOptions = NSISO8601DateFormatWithInternetDateTime | NSISO8601DateFormatWithFractionalSeconds;
    return [formatter stringFromDate:date];
}

static void output(id object) {
    NSError *error = nil;
    NSData *json = [NSJSONSerialization dataWithJSONObject:object options:0 error:&error];
    if (!json) fail(error.localizedDescription ?: @"JSON encoding failed");
    [[NSFileHandle fileHandleWithStandardOutput] writeData:json];
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        EKEventStore *store = [EKEventStore new];
        EKAuthorizationStatus status = [EKEventStore authorizationStatusForEntityType:EKEntityTypeEvent];
        if (status == EKAuthorizationStatusNotDetermined) {
            dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
            __block BOOL granted = NO;
            __block NSError *accessError = nil;
            [store requestFullAccessToEventsWithCompletion:^(BOOL allowed, NSError *error) {
                granted = allowed;
                accessError = error;
                dispatch_semaphore_signal(semaphore);
            }];
            if (dispatch_semaphore_wait(semaphore, dispatch_time(DISPATCH_TIME_NOW, 60 * NSEC_PER_SEC)) != 0)
                fail(@"Calendar permission prompt timed out");
            if (!granted) fail(accessError.localizedDescription ?: @"Calendar access denied");
        } else if (status != EKAuthorizationStatusFullAccess) {
            fail(@"Full Calendar read access is needed");
        }

        NSArray<EKCalendar *> *calendars = [store calendarsForEntityType:EKEntityTypeEvent];
        if (argc == 2 && strcmp(argv[1], "--list") == 0) {
            NSMutableArray *rows = [NSMutableArray array];
            for (EKCalendar *calendar in calendars) {
                [rows addObject:@{@"id": calendar.calendarIdentifier ?: @"",
                                  @"title": calendar.title ?: @"",
                                  @"source": calendar.source.title ?: @""}];
            }
            output(rows);
            return 0;
        }

        if (argc < 5 || strcmp(argv[1], "--events") != 0)
            fail(@"Use --list or --events START END CALENDAR_ID...");
        NSDate *start = parseDate([NSString stringWithUTF8String:argv[2]]);
        NSDate *end = parseDate([NSString stringWithUTF8String:argv[3]]);
        if (!start || !end || [end compare:start] != NSOrderedDescending)
            fail(@"Invalid date range");
        NSMutableSet<NSString *> *selected = [NSMutableSet set];
        for (int i = 4; i < argc; i++) [selected addObject:[NSString stringWithUTF8String:argv[i]]];
        NSMutableArray<EKCalendar *> *matched = [NSMutableArray array];
        for (EKCalendar *calendar in calendars)
            if ([selected containsObject:calendar.calendarIdentifier]) [matched addObject:calendar];
        if (matched.count != selected.count) fail(@"A selected calendar is unavailable");

        NSPredicate *predicate = [store predicateForEventsWithStartDate:start endDate:end calendars:matched];
        NSMutableArray *rows = [NSMutableArray array];
        for (EKEvent *event in [store eventsMatchingPredicate:predicate]) {
            NSString *calendarKey = event.calendar.calendarIdentifier;
            NSString *itemKey = event.calendarItemExternalIdentifier ?: event.eventIdentifier;
            if (!calendarKey || !itemKey || !event.startDate || !event.endDate)
                fail(@"An event lacked a stable identity or time; sync was not complete");
            NSString *occurrence = event.occurrenceDate ? formatDate(event.occurrenceDate) : @"single";
            NSString *key = [NSString stringWithFormat:@"%@:%@:%@", calendarKey, itemKey, occurrence];
            [rows addObject:@{@"key": key,
                              @"calendar_key": calendarKey,
                              @"title": event.title ?: @"Untitled event",
                              @"start": formatDate(event.startDate),
                              @"end": formatDate(event.endDate),
                              @"all_day": @(event.isAllDay)}];
        }
        output(@{@"complete": @YES, @"events": rows});
    }
    return 0;
}
